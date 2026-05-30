/**
 * PROMEOS — SiteRequiredState (Sprint P1.S6).
 *
 * EmptyState métier utilisé par les vues énergie qui ne supportent QUE
 * `scope=site` ou `scope=meter` côté backend (Semaine type, Coût &
 * contrat, Marché & exposition).
 *
 * Au lieu d'appeler l'API et laisser remonter un `ENERGY_SCOPE_INVALID`
 * en rouge, on guide l'utilisateur : « Sélectionnez un site pour
 * analyser cette vue. »
 *
 * Doctrine : aucun calcul métier — c'est uniquement de l'UX.
 */
import { Building2, MapPin } from 'lucide-react';
import { EmptyState } from '../index';

const DEFAULT_TITLE = 'Sélectionnez un site pour analyser cette vue.';
const DEFAULT_TEXT =
  "Cette analyse n'est disponible qu'au niveau d'un site (ou d'un compteur). Choisissez un site dans le sélecteur de périmètre.";

export default function SiteRequiredState({
  title = DEFAULT_TITLE,
  text = DEFAULT_TEXT,
  ctaLabel = 'Choisir un site',
  onChooseSite,
  className = '',
  testId = 'site-required-state',
}) {
  return (
    <div className={className} data-testid={testId}>
      <EmptyState
        variant="unconfigured"
        icon={Building2}
        title={title}
        text={text}
        ctaLabel={onChooseSite ? ctaLabel : undefined}
        onCta={onChooseSite}
        actions={
          !onChooseSite ? (
            <p className="text-[11px] text-gray-400 inline-flex items-center gap-1">
              <MapPin size={11} aria-hidden="true" />
              Sélecteur de scope disponible en haut de page.
            </p>
          ) : null
        }
      />
    </div>
  );
}
