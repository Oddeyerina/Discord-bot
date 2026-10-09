export default function Status({ message, error }: { message: string; error: string }) {
  return <>{message && <p role="status" className="rounded-lg bg-emerald-950 p-3 text-emerald-300">{message}</p>}{error && <p role="alert" className="rounded-lg bg-red-950 p-3 text-red-300">{error}</p>}</>;
}
