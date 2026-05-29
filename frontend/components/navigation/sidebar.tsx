'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { Button } from '@/components/ui/button';
import { 
  BarChart3, Upload, Settings, LogOut, Home, Menu
} from 'lucide-react';
import { useState } from 'react';

export default function Sidebar() {
  const pathname = usePathname();
  const { logout, user } = useAuth();
  const [isOpen, setIsOpen] = useState(false);

  const navItems = [
    { href: '/dashboard', icon: Home, label: 'Dashboard', roles: ['ADMIN', 'ANALYST', 'VIEWER'] },
    { href: '/ingest', icon: Upload, label: 'Ingest Data', roles: ['ADMIN', 'ANALYST'] },
    { href: '/analytics', icon: BarChart3, label: 'Analytics', roles: ['ADMIN', 'ANALYST', 'VIEWER'] },
  ];

  const userRole = user?.role || 'VIEWER';
  const filteredItems = navItems.filter(item => item.roles.includes(userRole));

  const isActive = (href: string) => pathname === href;

  return (
    <>
      {/* Mobile toggle */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="md:hidden fixed top-4 left-4 z-50 p-2"
      >
        <Menu className="h-6 w-6" />
      </button>

      {/* Sidebar */}
      <div
        className={`fixed md:relative md:flex flex-col w-64 bg-background border-r min-h-screen transition-all duration-300 z-40 ${
          isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        {/* Header */}
        <div className="p-6 border-b">
          <h1 className="text-xl font-bold">Breathe ESG</h1>
          <p className="text-xs text-muted-foreground mt-1">{userRole}</p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-6 space-y-2">
          {filteredItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.href);
            return (
              <Link key={item.href} href={item.href} onClick={() => setIsOpen(false)}>
                <div
                  className={`flex items-center gap-3 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    active
                      ? 'bg-primary text-primary-foreground'
                      : 'text-foreground hover:bg-muted'
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  {item.label}
                </div>
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t space-y-2">
          <p className="text-xs text-muted-foreground px-4 py-2">
            {user?.user.email}
          </p>
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start"
            onClick={logout}
          >
            <LogOut className="h-4 w-4 mr-2" />
            Logout
          </Button>
        </div>
      </div>

      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 md:hidden z-30"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  );
}
