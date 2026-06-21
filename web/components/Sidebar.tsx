'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';

const NAV = [
  { href: '/', label: 'Dashboard', icon: '◈' },
  { href: '/editais', label: 'Editais', icon: '≡' },
  { href: '/configuracoes', label: 'Configurações', icon: '⚙' },
];

interface SidebarProps {
  user?: { name: string; email: string } | null;
}

export function Sidebar({ user }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();

  async function handleLogout() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push('/login');
  }

  const initials = (user?.name ?? '')
    .split(' ')
    .slice(0, 2)
    .map((n) => n[0] ?? '')
    .join('')
    .toUpperCase() || '?';

  return (
    <aside className="w-56 flex-shrink-0 flex flex-col bg-slate-950 border-r border-slate-800">
      {/* Logo */}
      <div className="px-5 pt-7 pb-6 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <span className="text-indigo-400 text-lg font-bold">⬡</span>
          <span className="text-white font-semibold tracking-tight">
            Licitações<span className="text-indigo-400">.IA</span>
          </span>
        </div>
        <p className="mt-1.5 text-xs text-slate-500 leading-snug">
          Maquinário pesado &amp; agrícola
        </p>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {NAV.map(({ href, label, icon }) => {
          const active = pathname === href || (href !== '/' && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={[
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all',
                active
                  ? 'bg-indigo-600/20 text-indigo-300 font-medium'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800',
              ].join(' ')}
            >
              <span className="text-base leading-none">{icon}</span>
              {label}
            </Link>
          );
        })}
      </nav>

      {/* User */}
      {user && (
        <div className="px-3 py-3 border-t border-slate-800">
          <div className="flex items-center gap-2 px-2 py-1.5 mb-1">
            <div className="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center text-xs font-bold text-white flex-shrink-0">
              {initials}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium text-slate-300 truncate">{user.name}</p>
              <p className="text-xs text-slate-600 truncate">{user.email}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full text-left px-2 py-1.5 text-xs text-slate-500 hover:text-slate-300 rounded-lg hover:bg-slate-800 transition-all"
          >
            Sair →
          </button>
        </div>
      )}
    </aside>
  );
}
