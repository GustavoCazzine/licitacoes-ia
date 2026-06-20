'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV = [
  { href: '/', label: 'Dashboard', icon: '◈' },
  { href: '/editais', label: 'Editais', icon: '≡' },
];

export function Sidebar() {
  const pathname = usePathname();

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

      {/* Footer */}
      <div className="px-5 py-4 border-t border-slate-800">
        <p className="text-xs text-slate-600">v0.1.0 · MVP</p>
        <p className="text-xs text-slate-600 mt-0.5">Piracicaba, SP</p>
      </div>
    </aside>
  );
}
