import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api";

/** List + create + patch + delete for one per-user resource. Every mutation refreshes the derived views too. */
export function useCrud<T extends { id: string }, P>(key: string, path: string, params = "") {
  const queryClient = useQueryClient();
  const list = useQuery({ queryKey: [key, params], queryFn: () => apiGet<T[]>(`${path}${params}`), retry: false });
  const refresh = () => queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] !== "me" });

  const create = useMutation({
    mutationFn: (input: P) => apiPost<T>(path, input),
    onSuccess: () => { toast.success("Kayıt eklendi"); refresh(); },
    onError: () => toast.error("Kayıt eklenemedi, alanları kontrol et"),
  });
  const update = useMutation({
    mutationFn: ({ id, input }: { id: string; input: Partial<P> | Record<string, unknown> }) => apiPatch<T>(`${path}/${id}`, input),
    onSuccess: () => { toast.success("Güncellendi"); refresh(); },
    onError: () => toast.error("Güncellenemedi"),
  });
  const remove = useMutation({
    mutationFn: (id: string) => apiDelete<void>(`${path}/${id}`),
    onSuccess: () => { toast.success("Silindi"); refresh(); },
    onError: () => toast.error("Silinemedi"),
  });

  return { items: list.data ?? [], isLoading: list.isLoading, create, update, remove, refresh };
}
