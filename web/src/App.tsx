import { NavLink, Navigate, Route, Routes } from 'react-router-dom';
import { Catalog } from './pages/Catalog';
import { Overview } from './pages/Overview';
import { Pipeline } from './pages/Pipeline';
import { Placeholder } from './pages/Placeholder';

const NAV = [
  { to: '/overview', label: 'Tổng quan' },
  { to: '/pipeline', label: 'Sức khỏe pipeline' },
  { to: '/explore', label: 'Khám phá' },
  { to: '/analysis', label: 'Phân tích' },
  { to: '/catalog', label: 'Catalog' },
];

export function App() {
  return (
    <div className="shell">
      <nav className="side">
        <div className="brand">
          QTDL<span>warehouse</span>
        </div>
        {NAV.map((n) => (
          <NavLink key={n.to} to={n.to} className={({ isActive }) => (isActive ? 'active' : undefined)}>
            {n.label}
          </NavLink>
        ))}
      </nav>
      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/overview" replace />} />
          <Route path="/overview" element={<Overview />} />
          <Route path="/pipeline" element={<Pipeline />} />
          <Route path="/catalog" element={<Catalog />} />
          <Route
            path="/explore"
            element={
              <Placeholder
                title="Khám phá"
                milestone="M6"
                todo="Lọc theo dimension, xem độ đo, so sánh nhóm — đọc analytics.v_* qua /explore/facts."
              />
            }
          />
          <Route
            path="/analysis"
            element={
              <Placeholder
                title="Phân tích"
                milestone="M6"
                todo="Tương quan, regression đã tính sẵn từ notebook, đọc qua /analysis/*."
              />
            }
          />
          <Route path="*" element={<Navigate to="/overview" replace />} />
        </Routes>
      </main>
    </div>
  );
}
