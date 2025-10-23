import React, { useEffect, useRef } from 'react';
import clsx from 'clsx';

export type ScrollViewEffect = 'slide' | 'fade' | '';

export type ScrollViewItemProps = {
  item: any;
  effect?: ScrollViewEffect;
  onIntersect?: (
    item?: any,
    entry?: IntersectionObserverEntry,
  ) => boolean | void;
  children?: React.ReactNode;
};

const observerOptions = {
  threshold: [0, 0.1],
};

export const Item: React.FC<ScrollViewItemProps> = props => {
  const { item, effect, children, onIntersect } = props;
  const itemRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!onIntersect) return undefined;

    const observer = new IntersectionObserver(([entry]) => {
      if (entry.intersectionRatio > 0) {
        // Determine from the callback result whether to keep observing
        if (!onIntersect(item, entry)) {
          observer.unobserve(entry.target);
        }
      }
    }, observerOptions);

    if (itemRef.current) {
      observer.observe(itemRef.current);
    }
    return () => {
      observer.disconnect();
    };
  }, [item, onIntersect]);

  return (
    <div
      className={clsx('ScrollView-item', {
        'slide-in-right-item': effect === 'slide',
        'A-fadeIn': effect === 'fade',
      })}
      ref={itemRef}
    >
      {children}
    </div>
  );
};
