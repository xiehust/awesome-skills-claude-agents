import { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import clsx from 'clsx';

interface NavItem {
  path: string;
  label: string;
  icon: string;
}

const navItems: NavItem[] = [
  { path: '/', label: 'Dashboard', icon: 'dashboard' },
  { path: '/chat', label: 'Chat', icon: 'chat' },
  { path: '/agents', label: 'Agent Management', icon: 'smart_toy' },
  { path: '/skills', label: 'Skill Management', icon: 'construction' },
  { path: '/plugins', label: 'Plugin Management', icon: 'extension' },
  { path: '/mcp', label: 'MCP Management', icon: 'dns' },
];

const bottomNavItems: NavItem[] = [
  { path: '/settings', label: 'Settings', icon: 'settings' },
  { path: '/help', label: 'Help', icon: 'help' },
];

export default function Sidebar() {
  const location = useLocation();
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <aside className="w-16 bg-dark-bg border-r border-dark-border flex flex-col">
      {/* Logo */}
      <div className="h-16 flex items-center justify-center border-b border-dark-border">
        <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
          <span className="material-symbols-outlined text-primary">smart_toy</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-2 space-y-1">
        {navItems.map((item) => (
          <div
            key={item.path}
            className="relative"
            onMouseEnter={() => setHoveredItem(item.path)}
            onMouseLeave={() => setHoveredItem(null)}
          >
            <NavLink
              to={item.path}
              className={clsx(
                'flex items-center justify-center p-3 rounded-lg transition-colors',
                isActive(item.path)
                  ? 'bg-primary text-white'
                  : 'text-muted hover:bg-dark-hover hover:text-white'
              )}
            >
              <span className="material-symbols-outlined text-xl">{item.icon}</span>
            </NavLink>

            {/* Tooltip */}
            {hoveredItem === item.path && (
              <div className="absolute left-full ml-2 px-3 py-2 bg-dark-card border border-dark-border rounded-lg shadow-xl whitespace-nowrap z-50 pointer-events-none">
                <span className="text-sm text-white">{item.label}</span>
              </div>
            )}
          </div>
        ))}
      </nav>

      {/* Bottom navigation */}
      <div className="py-4 px-2 border-t border-dark-border space-y-1">
        {bottomNavItems.map((item) => (
          <div
            key={item.path}
            className="relative"
            onMouseEnter={() => setHoveredItem(item.path)}
            onMouseLeave={() => setHoveredItem(null)}
          >
            <NavLink
              to={item.path}
              className={clsx(
                'flex items-center justify-center p-3 rounded-lg transition-colors',
                isActive(item.path)
                  ? 'bg-primary text-white'
                  : 'text-muted hover:bg-dark-hover hover:text-white'
              )}
            >
              <span className="material-symbols-outlined text-xl">{item.icon}</span>
            </NavLink>

            {/* Tooltip */}
            {hoveredItem === item.path && (
              <div className="absolute left-full ml-2 px-3 py-2 bg-dark-card border border-dark-border rounded-lg shadow-xl whitespace-nowrap z-50 pointer-events-none">
                <span className="text-sm text-white">{item.label}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </aside>
  );
}
