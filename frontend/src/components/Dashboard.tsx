import React, { useState, useEffect } from 'react';
import { apiService, ScheduleRun } from '../services/api';
import './Dashboard.css';

interface DashboardProps {}

const Dashboard: React.FC<DashboardProps> = () => {
  const [scheduleRuns, setScheduleRuns] = useState<ScheduleRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadScheduleRuns();
  }, []);

  const loadScheduleRuns = async () => {
    try {
      setLoading(true);
      const runs = await apiService.getScheduleRuns();
      setScheduleRuns(runs);
      setError(null);
    } catch (err) {
      setError('Failed to load schedule runs');
      console.error('Error loading schedule runs:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRun = async () => {
    try {
      const name = `Schedule Run ${new Date().toLocaleString()}`;
      await apiService.createScheduleRun({
        name,
        description: 'Generated from dashboard'
      });
      loadScheduleRuns();
    } catch (err) {
      setError('Failed to create schedule run');
      console.error('Error creating schedule run:', err);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return '#4caf50';
      case 'running': return '#ff9800';
      case 'failed': return '#f44336';
      default: return '#757575';
    }
  };

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Production Scheduling Dashboard</h1>
        <button className="btn btn-primary" onClick={handleCreateRun}>
          New Schedule Run
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="stats-grid">
        <div className="stat-card">
          <h3>Total Runs</h3>
          <div className="stat-number">{scheduleRuns.length}</div>
        </div>
        <div className="stat-card">
          <h3>Completed</h3>
          <div className="stat-number">
            {scheduleRuns.filter(r => r.status === 'completed').length}
          </div>
        </div>
        <div className="stat-card">
          <h3>Running</h3>
          <div className="stat-number">
            {scheduleRuns.filter(r => r.status === 'running').length}
          </div>
        </div>
        <div className="stat-card">
          <h3>Failed</h3>
          <div className="stat-number">
            {scheduleRuns.filter(r => r.status === 'failed').length}
          </div>
        </div>
      </div>

      <div className="runs-section">
        <h2>Recent Schedule Runs</h2>
        <div className="runs-list">
          {scheduleRuns.length === 0 ? (
            <div className="empty-state">No schedule runs yet</div>
          ) : (
            scheduleRuns.slice(0, 10).map(run => (
              <div key={run.id} className="run-card">
                <div className="run-header">
                  <h3>{run.name}</h3>
                  <span 
                    className="status-badge"
                    style={{ backgroundColor: getStatusColor(run.status) }}
                  >
                    {run.status}
                  </span>
                </div>
                <div className="run-details">
                  {run.description && <p>{run.description}</p>}
                  <div className="run-stats">
                    {run.makespan && <span>Makespan: {run.makespan.toFixed(1)}</span>}
                    {run.total_orders && <span>Orders: {run.total_orders}</span>}
                    {run.total_late_days !== null && <span>Late Days: {run.total_late_days}</span>}
                  </div>
                  <div className="run-times">
                    <small>Created: {new Date(run.created_at).toLocaleString()}</small>
                    {run.completed_at && (
                      <small>Completed: {new Date(run.completed_at).toLocaleString()}</small>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;