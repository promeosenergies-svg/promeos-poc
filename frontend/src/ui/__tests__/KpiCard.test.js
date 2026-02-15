/**
 * PROMEOS — Tests for KpiCard resolveIcon helper
 * Prevents regression: KpiCard must accept icon as Component OR ReactElement.
 */
import { describe, it, expect } from 'vitest';
import { createElement, isValidElement } from 'react';
import { resolveIcon } from '../KpiCard';

// Mock component (simulates lucide-react icon)
function MockIcon(props) {
  return createElement('svg', props);
}

describe('resolveIcon', () => {
  it('returns a React element when given a Component function', () => {
    const result = resolveIcon(MockIcon, { size: 22 });
    expect(isValidElement(result)).toBe(true);
  });

  it('passes props to component', () => {
    const result = resolveIcon(MockIcon, { size: 22, className: 'text-white' });
    expect(result.props.size).toBe(22);
    expect(result.props.className).toBe('text-white');
  });

  it('returns the element as-is when given a ReactElement', () => {
    const element = createElement(MockIcon, { size: 18 });
    const result = resolveIcon(element);
    expect(isValidElement(result)).toBe(true);
    expect(result).toBe(element); // exact same reference
  });

  it('returns null for null input', () => {
    expect(resolveIcon(null)).toBeNull();
  });

  it('returns null for undefined input', () => {
    expect(resolveIcon(undefined)).toBeNull();
  });

  it('returns null for a string', () => {
    expect(resolveIcon('not-a-component')).toBeNull();
  });

  it('returns null for a plain object', () => {
    expect(resolveIcon({ type: 'svg' })).toBeNull();
  });

  it('returns null for a number', () => {
    expect(resolveIcon(42)).toBeNull();
  });
});
