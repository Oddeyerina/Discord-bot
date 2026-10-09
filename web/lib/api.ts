export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || '';

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}/api${path}`, {
    ...init,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...init.headers },
    cache: 'no-store',
  });
  if (response.status === 401 && typeof window !== 'undefined' && !path.startsWith('/auth/login')) {
    window.location.href = '/login';
  }
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const detail: unknown = (await response.json()).detail;
      if (typeof detail === 'string') message = detail;
      else if (Array.isArray(detail)) message = detail.map(item => item.msg || String(item)).join('; ');
    } catch { /* Empty response. */ }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export type Embed = {
  title: string; description: string; color: string; footer: string; thumbnail: string; image: string;
};
export const emptyEmbed: Embed = { title: '', description: '', color: '#5865F2', footer: '', thumbnail: '', image: '' };
export type GuildData = {
  channels: { id: string; name: string; type: string }[];
  roles: { id: string; name: string; position: number }[];
  emojis: { id: string; name: string; animated: boolean }[];
};
