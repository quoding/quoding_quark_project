/* QUARK — 공용 카드 조각 (CardHead / Gauge) */
import type { ReactNode } from 'react';
import { Icon, type IconName } from '@/components/Icon';

interface CardHeadProps {
  icon?: IconName;
  title: ReactNode;
  meta?: ReactNode;
  metaAcc?: boolean;
}

export function CardHead({ icon, title, meta, metaAcc }: CardHeadProps) {
  return (
    <div className="card-h">
      {icon && (
        <span className="ico">
          <Icon name={icon} />
        </span>
      )}
      <span className="ttl">{title}</span>
      {meta != null && meta !== false && <span className={'meta' + (metaAcc ? ' acc' : '')}>{meta}</span>}
    </div>
  );
}

interface GaugeProps {
  value: number;
  label: string;
  unit: string;
  kind?: 'ok' | 'warn' | 'bad';
}

export function Gauge({ value, label, unit, kind }: GaugeProps) {
  const k = kind || (value > 80 ? 'bad' : value > 60 ? 'warn' : 'ok');
  return (
    <div style={{ flex: 1, minWidth: 0 }}>
      <div className="between" style={{ marginBottom: 6 }}>
        <span style={{ fontSize: 11.5, color: 'var(--tx-mid)' }}>{label}</span>
        <span className="mono" style={{ fontSize: 12.5, color: 'var(--tx-hi)', fontWeight: 600 }}>
          {value}
          {unit}
        </span>
      </div>
      <div className={'bar ' + k}>
        <i style={{ width: value + '%' }} />
      </div>
    </div>
  );
}
