import { Navigate, Outlet } from 'react-router-dom';
import { useAuth, type UserRole } from '../store/AuthContext.tsx';

export function ProtectedRoute({ allowedRoles }: { allowedRoles?: readonly UserRole[] }) {
  const { token, role } = useAuth();
  if (!token) return <Navigate to="/login" replace />;
  if (allowedRoles && (!role || !allowedRoles.includes(role))) {
    return <Navigate to="/dashboard" replace />;
  }
  return <Outlet />;
}
