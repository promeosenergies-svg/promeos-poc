import { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Search } from 'lucide-react';
import Sidebar from './Sidebar';
import Breadcrumb from './Breadcrumb';
import ScopeSwitcher from './ScopeSwitcher';
import { trackRouteChange } from '../services/tracker';

export default function AppShell() {
  const location = useLocation();

  useEffect(() => {
    trackRouteChange(location.pathname);
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between sticky top-0 z-10">
          <div className="flex items-center gap-4">
            <Breadcrumb />
            <div className="relative">
              <ScopeSwitcher />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Rechercher..."
                className="pl-9 pr-4 py-2 w-52 bg-gray-50 border border-gray-200 rounded-lg text-sm
                  placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white"
              />
            </div>
            <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold">
              P
            </div>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
