import {
  buildViewingModePayload,
  formatViewingModeSize,
  normalizeViewingModeSize,
  resolveViewingModeDeviceType,
} from '@/c-utils/viewing-mode';
import {
  FRAME_LAYOUT_MOBILE,
  FRAME_LAYOUT_PAD,
  FRAME_LAYOUT_PAD_INTENSIVE,
  FRAME_LAYOUT_PC,
} from '@/c-constants/uiConstants';

describe('viewing-mode utilities', () => {
  it('normalizes and formats measured sizes', () => {
    expect(normalizeViewingModeSize(357.6, 608.4)).toEqual({
      width: 358,
      height: 608,
    });
    expect(formatViewingModeSize({ width: 358, height: 608 })).toBe(
      '358*608px',
    );
  });

  it('resolves device type from runtime layout data', () => {
    expect(
      resolveViewingModeDeviceType({
        frameLayout: FRAME_LAYOUT_MOBILE,
        inMobile: false,
      }),
    ).toBe('mobile');
    expect(
      resolveViewingModeDeviceType({
        frameLayout: FRAME_LAYOUT_PAD,
        inMobile: false,
      }),
    ).toBe('desktop');
    expect(
      resolveViewingModeDeviceType({
        frameLayout: FRAME_LAYOUT_PAD_INTENSIVE,
        inMobile: false,
      }),
    ).toBe('desktop');
    expect(
      resolveViewingModeDeviceType({
        frameLayout: FRAME_LAYOUT_PC,
        inMobile: true,
      }),
    ).toBe('mobile');
    expect(
      resolveViewingModeDeviceType({
        frameLayout: FRAME_LAYOUT_PC,
        inMobile: false,
      }),
    ).toBe('desktop');
  });

  it('prefers container size when building the viewing mode payload', () => {
    expect(
      buildViewingModePayload({
        deviceType: 'mobile',
        windowSize: { width: 390, height: 844 },
        containerSize: { width: 358, height: 608 },
      }),
    ).toEqual({
      device_type: 'mobile',
      container_size: '358*608px',
    });
  });

  it('falls back to the window size when container size is unavailable', () => {
    expect(
      buildViewingModePayload({
        deviceType: 'desktop',
        windowSize: { width: 1280, height: 720 },
        containerSize: null,
      }),
    ).toEqual({
      device_type: 'desktop',
      container_size: '1280*720px',
    });
  });
});
