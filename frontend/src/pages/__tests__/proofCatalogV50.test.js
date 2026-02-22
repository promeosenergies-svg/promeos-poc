/**
 * PROMEOS V50 — Proof Catalog V2 + Templates + Expected Proofs UX (source guards)
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const src = (rel) =>
  fs.readFileSync(path.resolve(__dirname, '..', '..', rel), 'utf-8');

const backendSrc = (rel) =>
  fs.readFileSync(
    path.resolve(__dirname, '..', '..', '..', '..', 'backend', rel),
    'utf-8',
  );

// 1. API module — V50 exports
describe('API exports V50 proof functions', () => {
  const api = src('services/api.js');

  it('exports getOperatProofCatalogV2', () => {
    expect(api).toContain('getOperatProofCatalogV2');
  });

  it('exports getIssueProofs', () => {
    expect(api).toContain('getIssueProofs');
  });

  it('exports createOperatProofTemplates', () => {
    expect(api).toContain('createOperatProofTemplates');
  });

  it('calls /proofs/catalog endpoint', () => {
    expect(api).toContain('/proofs/catalog');
  });

  it('calls /issues/ proofs endpoint', () => {
    expect(api).toContain('/issues/');
    expect(api).toContain('/proofs');
  });

  it('calls /proofs/templates endpoint', () => {
    expect(api).toContain('/proofs/templates');
  });
});

// 2. ActionDetailDrawer — V50 expected proofs + template CTA
describe('ActionDetailDrawer has V50 expected proofs UX', () => {
  const drawer = src('components/ActionDetailDrawer.jsx');

  it('imports getIssueProofs', () => {
    expect(drawer).toContain('getIssueProofs');
  });

  it('imports createOperatProofTemplates', () => {
    expect(drawer).toContain('createOperatProofTemplates');
  });

  it('has expectedProofs state', () => {
    expect(drawer).toContain('expectedProofs');
  });

  it('has generatingTemplates state', () => {
    expect(drawer).toContain('generatingTemplates');
  });

  it('has v50-expected-proofs test id', () => {
    expect(drawer).toContain('v50-expected-proofs');
  });

  it('shows proof title_fr', () => {
    expect(drawer).toContain('title_fr');
  });

  it('shows proof description_fr', () => {
    expect(drawer).toContain('description_fr');
  });

  it('shows proof examples_fr', () => {
    expect(drawer).toContain('examples_fr');
  });

  it('has confidence badge display', () => {
    expect(drawer).toContain('confidence');
  });

  it('has rationale_fr display', () => {
    expect(drawer).toContain('rationale_fr');
  });

  it('has generate templates CTA', () => {
    expect(drawer).toContain('v50-generate-templates-cta');
  });

  it('has handleGenerateTemplates function', () => {
    expect(drawer).toContain('handleGenerateTemplates');
  });

  it('calls createOperatProofTemplates with issue_code and proof_types', () => {
    expect(drawer).toContain('issue_code');
    expect(drawer).toContain('proof_types');
  });

  it('shows generation feedback via toast', () => {
    expect(drawer).toContain('modèle(s) créé(s)');
  });
});

// 3. Backend proof catalog
describe('Backend proof catalog V50', () => {
  const catalog = backendSrc('services/tertiaire_proof_catalog.py');

  it('has PROOF_TYPES dict', () => {
    expect(catalog).toContain('PROOF_TYPES');
  });

  it('has ISSUE_PROOF_MAPPING dict', () => {
    expect(catalog).toContain('ISSUE_PROOF_MAPPING');
  });

  it('has 6 proof types', () => {
    expect(catalog).toContain('attestation_operat');
    expect(catalog).toContain('dossier_modulation');
    expect(catalog).toContain('justificatif_exemption');
    expect(catalog).toContain('justificatif_multi_occupation');
    expect(catalog).toContain('preuve_surface_usage');
    expect(catalog).toContain('bail_titre_propriete');
  });

  it('has confidence levels', () => {
    expect(catalog).toContain('"high"');
    expect(catalog).toContain('"medium"');
  });

  it('has title_fr and description_fr fields', () => {
    expect(catalog).toContain('title_fr');
    expect(catalog).toContain('description_fr');
  });

  it('has examples_fr arrays', () => {
    expect(catalog).toContain('examples_fr');
  });
});

// 4. Backend proof templates
describe('Backend proof templates V50', () => {
  const templates = backendSrc('services/tertiaire_proof_templates.py');

  it('has render_template_md function', () => {
    expect(templates).toContain('def render_template_md');
  });

  it('has generate_proof_templates function', () => {
    expect(templates).toContain('def generate_proof_templates');
  });

  it('uses KBStore for doc creation', () => {
    expect(templates).toContain('KBStore');
    expect(templates).toContain('upsert_doc');
  });

  it('has dedup via get_doc', () => {
    expect(templates).toContain('get_doc');
  });

  it('supports action_id auto-link', () => {
    expect(templates).toContain('link_doc_to_action');
    expect(templates).toContain('action_id');
  });

  it('creates docs as draft status', () => {
    expect(templates).toContain('"draft"');
  });
});

// 5. Backend route
describe('Backend route has V50 endpoints', () => {
  const route = backendSrc('routes/tertiaire.py');

  it('imports V50 catalog functions', () => {
    expect(route).toContain('from services.tertiaire_proof_catalog import');
  });

  it('imports V50 template function', () => {
    expect(route).toContain('from services.tertiaire_proof_templates import');
    expect(route).toContain('generate_proof_templates');
  });

  it('has /proofs/catalog endpoint', () => {
    expect(route).toContain('proofs/catalog');
  });

  it('has /proofs/issue-mapping endpoint', () => {
    expect(route).toContain('proofs/issue-mapping');
  });

  it('has /issues/{issue_code}/proofs endpoint', () => {
    expect(route).toContain('issues/{issue_code}/proofs');
  });

  it('has /proofs/templates endpoint', () => {
    expect(route).toContain('proofs/templates');
  });

  it('has ProofTemplateBody schema', () => {
    expect(route).toContain('ProofTemplateBody');
  });
});
