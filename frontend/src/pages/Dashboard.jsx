/**
 * PROMEOS - Tableau de bord
 * Vue d'ensemble multi-sites — Design System V5.
 */
import { useEffect, useState, useCallback } from 'react';
import { getAlertes } from '../services/api';
import { Flame, Building2, AlertTriangle, TrendingUp } from 'lucide-react';
import { PageShell, KpiCard, Badge, Card, CardBody, EmptyState } from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';
import ErrorState from '../ui/ErrorState';
import { SkeletonCard } from '../ui/Skeleton';
import { useToast } from '../ui/ToastProvider';
import { useScope } from '../contexts/ScopeContext';

function Dashboard({ onUpgradeClick }) {
  const { toast } = useToast();
  const { orgSites, sitesCount, org, sitesLoading } = useScope();
  const [alertes, setAlertes] = useState([]);
  const [alertesCount, setAlertesCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const fetchAlertes = useCallback(() => {
    setLoading(true);
    setError(false);
    getAlertes({ resolue: false, limit: 50 })
      .then((data) => {
        setAlertes(data.alertes);
        setAlertesCount(data.total);
        setLoading(false);
      })
      .catch(() => {
        toast('Erreur lors du chargement du tableau de bord', 'error');
        setError(true);
        setLoading(false);
      });
  }, [toast]);

  useEffect(() => {
    fetchAlertes();
  }, [fetchAlertes]);

  const orgName = org?.nom;
  const sitesActifs = orgSites.filter(s => s.actif).length;

  // Etat erreur
  if (error && !loading) {
    return (
      <PageShell icon={Flame} title="Tableau de bord" subtitle="Erreur de chargement">
        <ErrorState
          message="Impossible de charger les données du tableau de bord."
          onRetry={fetchAlertes}
        />
      </PageShell>
    );
  }

  // Etat chargement
  if (loading || sitesLoading) {
    return (
      <PageShell icon={Flame} title="Tableau de bord" subtitle="Chargement...">
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
      title={orgName ? `${orgName} — Tableau de bord` : 'PROMEOS — Tableau de bord'}
      subtitle="Gestion énergétique multi-sites"
      actions={
        <Badge status="warning">Historique — utiliser Centre de Commande</Badge>
      }
    >
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <KpiCard
          icon={Building2}
          title="Sites total"
          value={sitesCount}
          color="bg-blue-600"
        />
        <KpiCard
          icon={TrendingUp}
          title="Sites actifs"
          value={sitesActifs}
          color="bg-emerald-600"
        />
        <KpiCard
          icon={AlertTriangle}
          title="Alertes actives"
          value={alertesCount}
          color="bg-red-600"
        />
      </div>

      {/* CTA si 0 sites */}
      {sitesCount === 0 && (
        <EmptyState
          icon={Building2}
          title="Aucun site enregistré"
          text="Importez vos sites pour commencer à suivre votre consommation énergétique et votre conformité réglementaire."
          ctaLabel="Importer mes sites"
          onCta={onUpgradeClick}
        />
      )}

      {/* Sites table */}
      {sitesCount > 0 && (
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
                  <Th>Statut</Th>
                </Tr>
              </Thead>
              <Tbody>
                {orgSites.slice(0, 10).map((site) => (
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
              Alertes actives
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
