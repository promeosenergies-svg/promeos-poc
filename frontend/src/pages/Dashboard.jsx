/**
 * PROMEOS - Dashboard Legacy
 * Vue d'ensemble des 120 sites — refactored with Design System V1.
 */
import { useEffect, useState } from 'react';
import { getSites, getAlertes, getOnboardingStatus } from '../services/api';
import { Flame, Building2, AlertTriangle, TrendingUp, Upload } from 'lucide-react';
import { PageShell, KpiCard, Badge, Card, CardBody, Button, EmptyState } from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';
import { SkeletonCard } from '../ui/Skeleton';
import { useToast } from '../ui/ToastProvider';

function Dashboard({ onUpgradeClick }) {
  const { toast } = useToast();
  const [sites, setSites] = useState([]);
  const [alertes, setAlertes] = useState([]);
  const [stats, setStats] = useState({
    totalSites: 0,
    sitesActifs: 0,
    alertesActives: 0,
  });
  const [orgName, setOrgName] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [sitesData, alertesData, onboardingData] = await Promise.all([
          getSites({ limit: 120 }),
          getAlertes({ resolue: false, limit: 50 }),
          getOnboardingStatus().catch(() => null),
        ]);
        setSites(sitesData.sites);
        setAlertes(alertesData.alertes);

        setStats({
          totalSites: sitesData.total,
          sitesActifs: sitesData.sites.filter(s => s.actif).length,
          alertesActives: alertesData.total,
        });

        if (onboardingData?.organisation_nom) {
          setOrgName(onboardingData.organisation_nom);
        }

        setLoading(false);
      } catch {
        toast('Erreur lors du chargement du dashboard', 'error');
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <PageShell icon={Flame} title="Dashboard" subtitle="Chargement...">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </PageShell>
    );
  }

  return (
    <PageShell
      icon={Flame}
      title={orgName ? `${orgName} — Dashboard` : 'PROMEOS Dashboard'}
      subtitle="Gestion energetique multi-sites"
      actions={
        <Badge status="warning">Legacy — utiliser Centre de Commande</Badge>
      }
    >
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <KpiCard
          icon={Building2}
          title="Total Sites"
          value={stats.totalSites}
          color="bg-blue-600"
        />
        <KpiCard
          icon={TrendingUp}
          title="Sites Actifs"
          value={stats.sitesActifs}
          color="bg-emerald-600"
        />
        <KpiCard
          icon={AlertTriangle}
          title="Alertes Actives"
          value={stats.alertesActives}
          color="bg-red-600"
        />
      </div>

      {/* CTA si 0 sites */}
      {stats.totalSites === 0 && (
        <EmptyState
          icon={Building2}
          title="Aucun site enregistre"
          text="Importez vos sites pour commencer a suivre votre consommation energetique et votre conformite reglementaire."
          ctaLabel="Importer mes sites"
          onCta={onUpgradeClick}
        />
      )}

      {/* Sites table */}
      {stats.totalSites > 0 && (
        <Card>
          <CardBody>
            <h2 className="text-lg font-bold text-gray-900 mb-4">Sites PROMEOS</h2>
            <Table>
              <Thead>
                <Tr>
                  <Th>Nom</Th>
                  <Th>Type</Th>
                  <Th>Ville</Th>
                  <Th>Region</Th>
                  <Th>Status</Th>
                </Tr>
              </Thead>
              <Tbody>
                {sites.slice(0, 10).map((site) => (
                  <Tr key={site.id}>
                    <Td className="font-medium">{site.nom}</Td>
                    <Td><Badge status="info">{site.type}</Badge></Td>
                    <Td>{site.ville}</Td>
                    <Td className="text-gray-500 text-sm">{site.region}</Td>
                    <Td>
                      {site.actif
                        ? <Badge status="success">Actif</Badge>
                        : <Badge status="neutral">Inactif</Badge>
                      }
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </CardBody>
        </Card>
      )}

      {/* Alertes recentes */}
      {alertes.length > 0 && (
        <Card>
          <CardBody>
            <h2 className="text-lg font-bold text-red-600 mb-4">
              <AlertTriangle size={18} className="inline mr-2" />
              Alertes Actives
            </h2>
            <div className="space-y-3">
              {alertes.slice(0, 5).map((alerte) => (
                <div
                  key={alerte.id}
                  className="flex items-center gap-4 p-4 bg-red-50 border-l-4 border-red-500 rounded-lg"
                >
                  <AlertTriangle size={20} className="text-red-500 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-gray-900">{alerte.titre}</p>
                    <p className="text-sm text-gray-500 mt-1">{alerte.description}</p>
                  </div>
                  <Badge
                    status={
                      alerte.severite === 'critical' ? 'danger'
                        : alerte.severite === 'warning' ? 'warning'
                        : 'info'
                    }
                  >
                    {alerte.severite}
                  </Badge>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      )}
    </PageShell>
  );
}

export default Dashboard;
