import { useCallback, useState } from "react";
import {
  getPath,
  getProgress,
  getReviews,
  startSession,
  turn,
  type DueItem,
  type Grade,
  type Level,
  type PathItem,
  type ProgressResponse,
  type TurnView,
} from "../lib/api";

export interface ChatMessage {
  role: "assistant" | "user";
  kind: "teach" | "quiz" | "answer" | "grade";
  text: string;
}

export interface SessionState {
  userId: string;
  topic: string;
  level: Level;
  sessionId: string | null;
  messages: ChatMessage[];
  streaming: string;
  view: TurnView | null;
  path: PathItem[];
  due: DueItem[];
  progress: ProgressResponse | null;
  loading: boolean;
  error: string | null;
}

export function useSession() {
  const [state, setState] = useState<SessionState>({
    userId: "demo",
    topic: "neural-networks",
    level: "student",
    sessionId: null,
    messages: [],
    streaming: "",
    view: null,
    path: [],
    due: [],
    progress: null,
    loading: false,
    error: null,
  });

  const patch = useCallback((p: Partial<SessionState>) => {
    setState((s) => ({ ...s, ...p }));
  }, []);

  const refreshDashboards = useCallback(
    async (userId: string, topic: string) => {
      const [path, reviews, progress] = await Promise.all([
        getPath(userId, topic),
        getReviews(userId),
        getProgress(userId, topic),
      ]);
      patch({ path: path.path, due: reviews.due, progress });
    },
    [patch],
  );

  const applyView = useCallback((view: TurnView): ChatMessage[] => {
    const msgs: ChatMessage[] = [];
    if (view.explanation) msgs.push({ role: "assistant", kind: "teach", text: view.explanation });
    if (view.question) msgs.push({ role: "assistant", kind: "quiz", text: view.question });
    return msgs;
  }, []);

  const start = useCallback(
    async (userId: string, topic: string, level: Level) => {
      patch({ loading: true, error: null, userId, topic, level, messages: [] });
      try {
        const view = await startSession(userId, topic, level);
        setState((s) => ({
          ...s,
          sessionId: view.session_id,
          view,
          messages: applyView(view),
          loading: false,
        }));
        await refreshDashboards(userId, topic);
      } catch (e) {
        patch({ loading: false, error: (e as Error).message });
      }
    },
    [patch, applyView, refreshDashboards],
  );

  const submitAnswer = useCallback(
    async (answer: string) => {
      if (!state.sessionId) return;
      const sessionId = state.sessionId;
      setState((s) => ({
        ...s,
        loading: true,
        streaming: "",
        messages: [...s.messages, { role: "user", kind: "answer", text: answer }],
      }));
      let grade: Grade | null = null;
      try {
        await turn(sessionId, answer, {
          onGrade: (g) => {
            grade = g;
            setState((s) => ({
              ...s,
              messages: [
                ...s.messages,
                { role: "assistant", kind: "grade", text: gradeLine(g) },
              ],
            }));
          },
          onToken: (t) => setState((s) => ({ ...s, streaming: s.streaming + t })),
          onDone: (view) => {
            setState((s) => {
              const msgs = [...s.messages];
              if (view.explanation)
                msgs.push({ role: "assistant", kind: "teach", text: view.explanation });
              if (view.question)
                msgs.push({ role: "assistant", kind: "quiz", text: view.question });
              return { ...s, view, streaming: "", messages: msgs, loading: false };
            });
          },
        });
        await refreshDashboards(state.userId, state.topic);
      } catch (e) {
        patch({ loading: false, error: (e as Error).message });
      }
      void grade;
    },
    [state.sessionId, state.userId, state.topic, patch, refreshDashboards],
  );

  const switchLevel = useCallback(
    async (level: Level) => {
      patch({ level });
      if (!state.sessionId) return;
      const sessionId = state.sessionId;
      setState((s) => ({ ...s, loading: true, streaming: "" }));
      try {
        await turn(
          sessionId,
          null,
          {
            onToken: (t) => setState((s) => ({ ...s, streaming: s.streaming + t })),
            onDone: (view) =>
              setState((s) => ({
                ...s,
                view,
                streaming: "",
                loading: false,
                messages: [
                  ...s.messages,
                  ...(view.explanation
                    ? [{ role: "assistant" as const, kind: "teach" as const, text: view.explanation }]
                    : []),
                  ...(view.question
                    ? [{ role: "assistant" as const, kind: "quiz" as const, text: view.question }]
                    : []),
                ],
              })),
          },
          level,
        );
      } catch (e) {
        patch({ loading: false, error: (e as Error).message });
      }
    },
    [state.sessionId, patch],
  );

  return { state, start, submitAnswer, switchLevel };
}

function gradeLine(g: Grade): string {
  const verdict = g.quality >= 3 ? "✅ Correct" : "❌ Not quite";
  return `${verdict} (quality ${g.quality}/5). ${g.feedback}`;
}
