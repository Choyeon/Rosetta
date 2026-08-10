/**
 * Feature Flag 读取器：统一封装 runtimeConfig.public 的 enableXxx 开关。
 *   - SSR / CSR 通用（useRuntimeConfig 自动处理）
 *   - 类型安全：每一个 feature key 都有显式声明
 *   - 所有开关默认 false（显式开启才生效），避免 runtimeConfig 缺字段时误判
 *
 * @example
 *   const { enableComments, enableBangumi } = useFeature();
 *   if (enableComments.value) { ... }
 */

export interface FeatureFlags {
  readonly enableComments: boolean;
  readonly enableBangumi: boolean;
  readonly enableAnime: boolean;
  readonly enableGallery: boolean;
  readonly enableDynamic: boolean;
  readonly enableGuestbook: boolean;
  readonly enableFriends: boolean;
  readonly enableSponsor: boolean;
  readonly enableMusic: boolean;
  readonly enableAnalytics: boolean;
  readonly enableEffects: boolean;
  readonly enableEncryption: boolean;
}

type FeatureKey = keyof FeatureFlags;

const DEFAULT_FLAGS: FeatureFlags = {
  enableComments: false,
  enableBangumi: false,
  enableAnime: false,
  enableGallery: false,
  enableDynamic: false,
  enableGuestbook: false,
  enableFriends: false,
  enableSponsor: false,
  enableMusic: false,
  enableAnalytics: false,
  enableEffects: false,
  enableEncryption: false,
} as const;

const ALL_KEYS: readonly FeatureKey[] = Object.freeze(
  Object.keys(DEFAULT_FLAGS) as FeatureKey[]
);

export function useFeature(): FeatureFlags {
  const runtime = useRuntimeConfig();
  const pub = runtime.public as Record<string, unknown>;

  const flags: Record<string, boolean> = {};
  for (const key of ALL_KEYS) {
    const raw = pub[key];
    flags[key] = typeof raw === "boolean" ? raw : DEFAULT_FLAGS[key];
  }

  return flags as FeatureFlags;
}

/**
 * 单独读取某一个 feature（模板里解构懒加载用）。
 */
export function useFeatureFlag<K extends FeatureKey>(key: K): Ref<FeatureFlags[K]> {
  const flags = useFeature();
  const val = flags[key];
  return ref(val);
}
