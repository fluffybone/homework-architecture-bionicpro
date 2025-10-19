import React, { useState } from 'react';
import { useKeycloak } from '@react-keycloak/web';

// Определяем тип для данных отчета для лучшей типизации
interface ReportData {
  user_id: number;
  user_name: string;
  prosthesis_model: string;
  avg_daily_usage: number;
  max_signal_value: number;
  last_seen_date: string;
  report_updated_at: string;
}

const ReportPage: React.FC = () => {
  const { keycloak, initialized } = useKeycloak();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reportData, setReportData] = useState<ReportData | null>(null); 

  const downloadReport = async () => {
    if (!keycloak?.token) {
      setError('Not authenticated');
      return;
    }

    console.log('Sending token to backend:', keycloak.token);
    try {
      setLoading(true);
      setError(null);
      setReportData(null); 

      const response = await fetch(`${process.env.REACT_APP_API_URL}/reports`, {
        headers: {
          'Authorization': `Bearer ${keycloak.token}`
        }
      });

      console.log("Response from backend:", response);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Request failed with status ${response.status}`);
      }

      const data: ReportData = await response.json();
      setReportData(data); 

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  if (!initialized) {
    return <div>Loading Keycloak...</div>;
  }

  // Экран для неаутентифицированных пользователей
  if (!keycloak.authenticated) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
        <h1 className="text-2xl font-bold mb-4">Please Login</h1>
        <button
          onClick={() => keycloak.login()}
          className="px-6 py-2 font-semibold bg-blue-500 text-white rounded-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-opacity-75"
        >
          Login
        </button>
      </div>
    );
  }

  // Основной экран для аутентифицированных пользователей
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 p-4">
      <div className="w-full max-w-md p-8 bg-white rounded-lg shadow-xl">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">Usage Reports</h1>
          <button
            onClick={() => keycloak.logout()}
            className="px-4 py-2 text-sm bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
          >
            Logout ({keycloak.tokenParsed?.preferred_username})
          </button>
        </div>
        
        <button
          onClick={downloadReport}
          disabled={loading}
          className={`w-full px-4 py-3 font-bold bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors ${
            loading ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {loading ? 'Generating Report...' : 'Download My Report'}
        </button>

        {error && (
          <div className="mt-4 p-4 bg-red-100 text-red-700 rounded-lg">
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Блок для отображения полученного отчета */}
        {reportData && (
          <div className="mt-6 p-4 border border-gray-200 rounded-lg">
            <h2 className="text-xl font-semibold mb-2">Your Report</h2>
            <ul className="space-y-1 text-gray-700">
              <li><strong>User ID:</strong> {reportData.user_id}</li>
              <li><strong>Name:</strong> {reportData.user_name}</li>
              <li><strong>Model:</strong> {reportData.prosthesis_model}</li>
              <li><strong>Avg. Usage:</strong> {reportData.avg_daily_usage.toFixed(2)}</li>
              <li><strong>Max Signal:</strong> {reportData.max_signal_value}</li>
              <li><strong>Last Seen:</strong> {new Date(reportData.last_seen_date).toLocaleDateString()}</li>
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReportPage;
