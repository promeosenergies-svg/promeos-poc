/**
 * PROMEOS — V96 Paiement & Refacturation
 * Matrice Facturé / Payeur / Centre de coûts.
 */
import { useState, useEffect, useCallback } from 'react';
import { BadgeEuro, Trash2 } from 'lucide-react';
import { Card, CardBody, Badge, EmptyState, PageShell } from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';
import { SkeletonCard } from '../ui/Skeleton';
import { getPaymentRules, deletePaymentRule } from '../services/api';

const LEVEL_BADGE = {
  portefeuille: { status: 'info', label: 'Portefeuille' },
  site: { status: 'success', label: 'Site' },
  contrat: { status: 'warning', label: 'Contrat' },
};

export default function PaymentRulesPage() {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchRules = useCallback(() => {
    setLoading(true);
    getPaymentRules()
      .then((data) => setRules(data.rules || []))
      .catch(() => setRules([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchRules();
  }, [fetchRules]);

  const handleDelete = async (id) => {
    if (!window.confirm('Supprimer cette règle de paiement ?')) return;
    try {
      await deletePaymentRule(id);
      fetchRules();
    } catch {
      /* ignore */
    }
  };

  // Group by level
  const portfolioRules = rules.filter((r) => r.level === 'portefeuille');
  const overrides = rules.filter((r) => r.level !== 'portefeuille');

  return (
    <PageShell
      icon={BadgeEuro}
      title="Paiement & Refacturation"
      subtitle="Matrice facturé / payeur / centre de coûts"
    >
      {loading ? (
        <div className="space-y-4">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : rules.length === 0 ? (
        <EmptyState
          icon={BadgeEuro}
          title="Aucune règle de paiement"
          text="Configurez qui reçoit la facture, qui paye et quel centre de coûts pour vos portefeuilles et sites."
        />
      ) : (
        <div className="space-y-6">
          {/* Section 1: Portefeuille rules */}
          <Card>
            <div className="px-5 py-3 border-b border-gray-100 flex justify-between items-center">
              <h3 className="font-semibold text-gray-800">Règles par portefeuille</h3>
            </div>
            {portfolioRules.length === 0 ? (
              <CardBody>
                <p className="text-sm text-gray-500">Aucune règle portefeuille configurée</p>
              </CardBody>
            ) : (
              <Table>
                <Thead>
                  <tr>
                    <Th>Portefeuille</Th>
                    <Th>EJ Facturée</Th>
                    <Th>EJ Payeur</Th>
                    <Th>Centre de coût</Th>
                    <Th></Th>
                  </tr>
                </Thead>
                <Tbody>
                  {portfolioRules.map((r) => (
                    <Tr key={r.id}>
                      <Td className="font-medium">#{r.portefeuille_id}</Td>
                      <Td>#{r.invoice_entity_id}</Td>
                      <Td>{r.payer_entity_id ? `#${r.payer_entity_id}` : '—'}</Td>
                      <Td>{r.cost_center || '—'}</Td>
                      <Td className="text-right">
                        <button
                          onClick={() => handleDelete(r.id)}
                          className="text-red-500 hover:text-red-700"
                        >
                          <Trash2 size={14} />
                        </button>
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            )}
          </Card>

          {/* Section 2: Overrides (site/contrat) */}
          {overrides.length > 0 && (
            <Card>
              <div className="px-5 py-3 border-b border-gray-100">
                <h3 className="font-semibold text-gray-800">Exceptions (site / contrat)</h3>
              </div>
              <Table>
                <Thead>
                  <tr>
                    <Th>Niveau</Th>
                    <Th>Cible</Th>
                    <Th>EJ Facturée</Th>
                    <Th>EJ Payeur</Th>
                    <Th>Centre de coût</Th>
                    <Th></Th>
                  </tr>
                </Thead>
                <Tbody>
                  {overrides.map((r) => (
                    <Tr key={r.id}>
                      <Td>
                        <Badge status={LEVEL_BADGE[r.level]?.status || 'info'}>
                          {LEVEL_BADGE[r.level]?.label || r.level}
                        </Badge>
                      </Td>
                      <Td className="font-medium">
                        {r.site_id
                          ? `Site #${r.site_id}`
                          : r.contract_id
                            ? `Contrat #${r.contract_id}`
                            : '—'}
                      </Td>
                      <Td>#{r.invoice_entity_id}</Td>
                      <Td>{r.payer_entity_id ? `#${r.payer_entity_id}` : '—'}</Td>
                      <Td>{r.cost_center || '—'}</Td>
                      <Td className="text-right">
                        <button
                          onClick={() => handleDelete(r.id)}
                          className="text-red-500 hover:text-red-700"
                        >
                          <Trash2 size={14} />
                        </button>
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </Card>
          )}
        </div>
      )}
    </PageShell>
  );
}
