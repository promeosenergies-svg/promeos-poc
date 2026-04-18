/**
 * PROMEOS — SolButton
 * 4 variants : primary (ink-900), secondary (paper+border), ghost (transparent),
 * agentic (calme-fg). Accepte `as="a"` pour rendre un <a href>.
 */
import React from 'react';

export default function SolButton({
  variant = 'primary',
  as: Tag = 'button',
  children,
  className = '',
  ...rest
}) {
  return (
    <Tag className={`sol-btn sol-btn--${variant} ${className}`.trim()} {...rest}>
      {children}
    </Tag>
  );
}
