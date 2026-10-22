import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'Radar de Notícias', description: 'Monitoramento de notícias públicas e comparador de declarações.' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="pt-BR"><body>{children}</body></html>;
}
