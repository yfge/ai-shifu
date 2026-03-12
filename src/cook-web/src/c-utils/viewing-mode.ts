import type {
  ViewingModeDeviceType,
  ViewingModePayload,
} from '@/c-api/studyV2';
import {
  FRAME_LAYOUT_MOBILE,
  FRAME_LAYOUT_PAD,
  FRAME_LAYOUT_PAD_INTENSIVE,
} from '@/c-constants/uiConstants';

export interface ViewingModeSize {
  width: number;
  height: number;
}

export interface RuntimeViewingModeState {
  deviceType: ViewingModeDeviceType;
  windowSize: ViewingModeSize | null;
  containerSize: ViewingModeSize | null;
}

const normalizeSizeValue = (value: number): number | null => {
  if (!Number.isFinite(value) || value <= 0) {
    return null;
  }
  return Math.max(1, Math.round(value));
};

export const normalizeViewingModeSize = (
  width: number,
  height: number,
): ViewingModeSize | null => {
  const normalizedWidth = normalizeSizeValue(width);
  const normalizedHeight = normalizeSizeValue(height);
  if (!normalizedWidth || !normalizedHeight) {
    return null;
  }
  return {
    width: normalizedWidth,
    height: normalizedHeight,
  };
};

export const formatViewingModeSize = (size: ViewingModeSize): string => {
  return `${size.width}*${size.height}px`;
};

export const resolveViewingModeDeviceType = ({
  frameLayout,
  inMobile,
}: {
  frameLayout: number;
  inMobile: boolean;
}): ViewingModeDeviceType => {
  if (inMobile || frameLayout === FRAME_LAYOUT_MOBILE) {
    return 'mobile';
  }
  if (
    frameLayout === FRAME_LAYOUT_PAD ||
    frameLayout === FRAME_LAYOUT_PAD_INTENSIVE
  ) {
    return 'tablet';
  }
  return 'desktop';
};

export const getCurrentWindowSize = (): ViewingModeSize | null => {
  if (typeof window === 'undefined') {
    return null;
  }
  const visualViewport = window.visualViewport;
  return normalizeViewingModeSize(
    visualViewport?.width ?? window.innerWidth,
    visualViewport?.height ?? window.innerHeight,
  );
};

const measureElementSize = (
  element?: Element | null,
): ViewingModeSize | null => {
  if (!element || typeof element.getBoundingClientRect !== 'function') {
    return null;
  }
  const rect = element.getBoundingClientRect();
  return normalizeViewingModeSize(rect.width, rect.height);
};

export const measureViewingModeContainerSize = (
  element?: HTMLElement | null,
): ViewingModeSize | null => {
  return (
    measureElementSize(element) ??
    measureElementSize(element?.parentElement ?? null)
  );
};

export const buildViewingModePayload = ({
  deviceType,
  windowSize,
  containerSize,
}: RuntimeViewingModeState): ViewingModePayload | undefined => {
  const effectiveSize = containerSize ?? windowSize;
  if (!effectiveSize) {
    return undefined;
  }
  return {
    container_size: formatViewingModeSize(effectiveSize),
    device_type: deviceType,
  };
};
