import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Licitações.IA',
  description: 'Inteligência em compras públicas — maquinário pesado e agrícola',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className="antialiased">{children}</body>
    </html>
  );
}
