import { Link, useLocation } from 'react-router-dom';
import './Sidebar.css';

export function Sidebar() {
  const location = useLocation();

  const menuItems = [
    { path: '/', label: '使用状況', icon: '📊' },
    { path: '/prompt-analysis', label: 'プロンプト分析', icon: '🔍' },
    { path: '/advice', label: '改善アドバイス', icon: '💡' },
  ];

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h2>Claude Analytics</h2>
      </div>
      <nav className="sidebar-nav">
        {menuItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`sidebar-nav-item ${location.pathname === item.path ? 'active' : ''}`}
          >
            <span className="sidebar-nav-icon">{item.icon}</span>
            <span className="sidebar-nav-label">{item.label}</span>
          </Link>
        ))}
      </nav>
    </div>
  );
}
