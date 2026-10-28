import { Route, Routes } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import LoginPage from "@/pages/LoginPage";
import OverviewPage from "@/pages/OverviewPage";
import DeliveriesPage from "@/pages/deliveries/DeliveriesPage";
import DeliveryDetailPage from "@/pages/deliveries/DeliveryDetailPage";
import FleetPage from "@/pages/fleet/FleetPage";
import ExceptionsPage from "@/pages/exceptions/ExceptionsPage";
import RecoveryPage from "@/pages/recovery/RecoveryPage";
import SimulationsPage from "@/pages/simulations/SimulationsPage";
import CopilotPage from "@/pages/copilot/CopilotPage";
import AnalyticsPage from "@/pages/analytics/AnalyticsPage";
import ApprovalsPage from "@/pages/approvals/ApprovalsPage";
import AuditPage from "@/pages/audit/AuditPage";
import SettingsPage from "@/pages/settings/SettingsPage";

function NotFound() {
  return (
    <div className="p-8">
      <h1 className="text-xl font-semibold">404</h1>
      <p className="text-muted-foreground">Page not found.</p>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<OverviewPage />} />
          <Route path="deliveries" element={<DeliveriesPage />} />
          <Route path="deliveries/:id" element={<DeliveryDetailPage />} />
          <Route path="fleet" element={<FleetPage />} />
          <Route path="exceptions" element={<ExceptionsPage />} />
          <Route path="recovery" element={<RecoveryPage />} />
          <Route path="simulations" element={<SimulationsPage />} />
          <Route path="copilot" element={<CopilotPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="approvals" element={<ApprovalsPage />} />
          <Route path="audit" element={<AuditPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Route>
    </Routes>
  );
}
