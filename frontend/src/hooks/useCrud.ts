import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api";
import { useT } from "@/lib/i18n";

/** List + create + patch + delete for one per-user resource. Every mutation refreshes the derived views too. */
export function useCrud<T extends { id: string }, P>(key: string, path: string, params = "") {
  const { t } = useT();
  const queryClient = useQueryClient();
  const list = useQuery({ queryKey: [key, params], queryFn: () => apiGet<T[]>(`${path}${params}`), retry: false });
  const refresh = () => queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] !== "me" });

  const create = useMutation({
    mutationFn: (input: P) => apiPost<T>(path, input),
    onSuccess: () => { toast.success(t("crud.added")); refresh(); },
    onError: () => toast.error(t("crud.addFailed")),
  });
  const update = useMutation({
    mutationFn: ({ id, input }: { id: string; input: Partial<P> | Record<string, unknown> }) => apiPatch<T>(`${path}/${id}`, input),
    onSuccess: () => { toast.success(t("crud.updated")); refresh(); },
    onError: () => toast.error(t("crud.updateFailed")),
  });
  const remove = useMutation({
    mutationFn: (id: string) => apiDelete<void>(`${path}/${id}`),
    onSuccess: () => { toast.success(t("crud.deleted")); refresh(); },
    onError: () => toast.error(t("crud.deleteFailed")),
  });

  return { items: list.data ?? [], isLoading: list.isLoading, create, update, remove, refresh };
}
