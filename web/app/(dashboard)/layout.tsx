import { createClient } from '@/lib/supabase/server';
import { Sidebar } from '@/components/Sidebar';

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  const userInfo = user
    ? {
        name: (user.user_metadata?.full_name as string | undefined) ?? user.email ?? '',
        email: user.email ?? '',
      }
    : null;

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50 text-gray-900 antialiased">
      <Sidebar user={userInfo} />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto px-6 py-8 lg:px-10">{children}</div>
        </main>
      </div>
    </div>
  );
}
