import './globals.css';
import type { Metadata } from 'next';

// Next.js automatically uses app/icon.png, app/icon.svg, or app/favicon.ico when present.
export const metadata: Metadata = { title: 'Morpho-Dashboard', description: 'Private bot dashboard' };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
