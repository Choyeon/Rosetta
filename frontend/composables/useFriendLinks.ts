/**
 * 友链公示数据。
 *
 * 声明式首屏数据必须走 useAPI（而不是 onMounted + apiFetch），
 * 否则 SSR 首帧拿到空列表、访客看到空白区块。
 */
import type { FriendLink } from '~~/types/api'
import { useAPI } from '~~/composables/useApi'

export const useFriendLinks = () => {
  const getFriendLinks = () => {
    return useAPI<FriendLink[]>('/friend-links', {
      default: () => []
    })
  }

  return { getFriendLinks }
}
