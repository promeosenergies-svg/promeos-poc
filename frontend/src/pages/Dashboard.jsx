/**
 * PROMEOS - Page Dashboard
 * Vue d'ensemble des 120 sites
 */
import { useEffect, useState } from 'react';
import { getSites, getAlertes } from '../services/api';
import { Flame, Building2, AlertTriangle, TrendingUp } from 'lucide-react';

function Dashboard() {
  const [sites, setSites] = useState([]);
  const [alertes, setAlertes] = useState([]);
  const [stats, setStats] = useState({
    totalSites: 0,
    sitesActifs: 0,
    alertesActives: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const sitesData = await getSites({ limit: 120 });
        setSites(sitesData.sites);

        const alertesData = await getAlertes({ resolue: false, limit: 50 });
        setAlertes(alertesData.alertes);

        setStats({
          totalSites: sitesData.total,
          sitesActifs: sitesData.sites.filter(s => s.actif).length,
          alertesActives: alertesData.total,
        });

        setLoading(false);
      } catch (error) {
        console.error('Erreur chargement dashboard:', error);
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        fontSize: '24px'
      }}>
        🔄 Chargement des données PROMEOS...
      </div>
    );
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: '32px'
    }}>
      {/* Header */}
      <div style={{ marginBottom: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
          <Flame style={{ width: '48px', height: '48px', color: '#fb923c' }} />
          <h1 style={{ fontSize: '36px', fontWeight: 'bold', color: 'white', margin: 0 }}>
            PROMEOS Dashboard
          </h1>
        </div>
        <p style={{ color: '#ddd6fe', fontSize: '18px', margin: 0 }}>
          Gestion énergétique multi-sites
        </p>
      </div>

      {/* Stats Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: '24px',
        marginBottom: '32px'
      }}>
        {/* Total Sites */}
        <div style={{
          background: 'white',
          borderRadius: '16px',
          padding: '24px',
          boxShadow: '0 10px 30px rgba(0,0,0,0.2)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <p style={{ color: '#6b7280', fontSize: '14px', margin: 0 }}>Total Sites</p>
              <p style={{ fontSize: '40px', fontWeight: 'bold', color: '#111827', margin: '8px 0 0 0' }}>
                {stats.totalSites}
              </p>
            </div>
            <Building2 style={{ width: '48px', height: '48px', color: '#3b82f6' }} />
          </div>
        </div>

        {/* Sites Actifs */}
        <div style={{
          background: 'white',
          borderRadius: '16px',
          padding: '24px',
          boxShadow: '0 10px 30px rgba(0,0,0,0.2)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <p style={{ color: '#6b7280', fontSize: '14px', margin: 0 }}>Sites Actifs</p>
              <p style={{ fontSize: '40px', fontWeight: 'bold', color: '#10b981', margin: '8px 0 0 0' }}>
                {stats.sitesActifs}
              </p>
            </div>
            <TrendingUp style={{ width: '48px', height: '48px', color: '#10b981' }} />
          </div>
        </div>

        {/* Alertes Actives */}
        <div style={{
          background: 'white',
          borderRadius: '16px',
          padding: '24px',
          boxShadow: '0 10px 30px rgba(0,0,0,0.2)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <p style={{ color: '#6b7280', fontSize: '14px', margin: 0 }}>Alertes Actives</p>
              <p style={{ fontSize: '40px', fontWeight: 'bold', color: '#ef4444', margin: '8px 0 0 0' }}>
                {stats.alertesActives}
              </p>
            </div>
            <AlertTriangle style={{ width: '48px', height: '48px', color: '#ef4444' }} />
          </div>
        </div>
      </div>

      {/* Sites récents */}
      <div style={{
        background: 'white',
        borderRadius: '16px',
        padding: '24px',
        marginBottom: '32px',
        boxShadow: '0 10px 30px rgba(0,0,0,0.2)'
      }}>
        <h2 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '16px' }}>
          Sites PROMEOS
        </h2>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                <th style={{ textAlign: 'left', padding: '12px', fontWeight: '600' }}>Nom</th>
                <th style={{ textAlign: 'left', padding: '12px', fontWeight: '600' }}>Type</th>
                <th style={{ textAlign: 'left', padding: '12px', fontWeight: '600' }}>Ville</th>
                <th style={{ textAlign: 'left', padding: '12px', fontWeight: '600' }}>Région</th>
                <th style={{ textAlign: 'left', padding: '12px', fontWeight: '600' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {sites.slice(0, 10).map((site) => (
                <tr key={site.id} style={{ borderBottom: '1px solid #e5e7eb' }}>
                  <td style={{ padding: '12px', fontWeight: '500' }}>{site.nom}</td>
                  <td style={{ padding: '12px' }}>
                    <span style={{
                      padding: '4px 12px',
                      background: '#dbeafe',
                      color: '#1e40af',
                      borderRadius: '6px',
                      fontSize: '13px'
                    }}>
                      {site.type}
                    </span>
                  </td>
                  <td style={{ padding: '12px' }}>{site.ville}</td>
                  <td style={{ padding: '12px', color: '#6b7280', fontSize: '14px' }}>
                    {site.region}
                  </td>
                  <td style={{ padding: '12px' }}>
                    {site.actif ? (
                      <span style={{
                        padding: '4px 12px',
                        background: '#d1fae5',
                        color: '#065f46',
                        borderRadius: '6px',
                        fontSize: '13px'
                      }}>
                        ✓ Actif
                      </span>
                    ) : (
                      <span style={{
                        padding: '4px 12px',
                        background: '#f3f4f6',
                        color: '#374151',
                        borderRadius: '6px',
                        fontSize: '13px'
                      }}>
                        Inactif
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Alertes récentes */}
      {alertes.length > 0 && (
        <div style={{
          background: 'white',
          borderRadius: '16px',
          padding: '24px',
          boxShadow: '0 10px 30px rgba(0,0,0,0.2)'
        }}>
          <h2 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '16px', color: '#ef4444' }}>
            🚨 Alertes Actives
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {alertes.slice(0, 5).map((alerte) => (
              <div
                key={alerte.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px',
                  padding: '16px',
                  background: '#fef2f2',
                  borderLeft: '4px solid #ef4444',
                  borderRadius: '8px'
                }}
              >
                <AlertTriangle style={{ width: '24px', height: '24px', color: '#ef4444' }} />
                <div style={{ flex: 1 }}>
                  <p style={{ fontWeight: '600', color: '#111827', margin: 0 }}>
                    {alerte.titre}
                  </p>
                  <p style={{ fontSize: '14px', color: '#6b7280', margin: '4px 0 0 0' }}>
                    {alerte.description}
                  </p>
                </div>
                <span style={{
                  padding: '6px 16px',
                  borderRadius: '6px',
                  fontSize: '13px',
                  fontWeight: '600',
                  background: alerte.severite === 'critical' ? '#dc2626' :
                             alerte.severite === 'warning' ? '#f97316' : '#3b82f6',
                  color: 'white'
                }}>
                  {alerte.severite}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;

