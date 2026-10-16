/**
 * useMessages —— 私信域（/api/messages*）的唯一前端出口。
 *
 * 后端这一族自上线起零前端消费：用户能收到点赞与评论通知，却没有任何地方能读私信。
 * 分工沿用 useFavorites（见其文件头）：
 * - 列表/会话正文**不在此封装**：两者的 URL 与 query 随分页、随选中的对端变化，
 *   封成固定签名会逼页面绕开 useAPI 单源（与收藏列表同口径）；
 * - 动词式走 apiFetch（交互/提交，401 自动刷新、失败统一 toast）。
 *
 * 后端契约要点（决定下面为什么这么写）：
 * 1. `GET /messages/{user_id}` **带副作用**：读取时把该对端发给我的未读消息全部置为已读。
 *    所以打开会话即清未读，页面不需要再补一次 read-all；`PUT /messages/read-all/{user_id}`
 *    只在「不打开会话直接标已读」这一条路径上有意义（列表上的按钮）。
 * 2. `PUT /messages/{message_id}/read`（按单条标已读）**刻意不包装**：上面的读口已经
 *    一次性把整个会话置为已读，前端不存在「只有某几条未读」的状态可展示，按条标已读
 *    没有真实消费点。宁可不包，也不留一个没人调的 wrapper 冒充覆盖。
 * 3. `POST /messages` 正文走 **JSON 请求体**（后端描述里写明原因：走 query string 会整条
 *    落进 nginx 访问日志，5000 字上限还会顶破请求头缓冲）。给自己发回 400、对端不存在回 404。
 * 4. 会话列表/会话正文都回裸分页对象 `{items,total,page,page_size,total_pages}`；
 *    列表的 `total` 是**对端数**，不是本页条数。
 */
import { apiFetch, silentApiFetch } from '~~/composables/useApi'

export interface MessagePeer {
  id: number
  username: string
  nickname?: string | null
  avatar?: string | null
}

export interface MessageLastLine {
  content: string
  created_at: string
  is_mine: boolean
}

export interface MessageConversationRow {
  user: MessagePeer
  last_message: MessageLastLine
  unread_count: number
}

export interface MessageConversationList {
  items: MessageConversationRow[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface MessageItem {
  id: number
  content: string
  is_mine: boolean
  is_read: boolean
  created_at: string
}

export interface MessageThread {
  items: MessageItem[]
  other_user: MessagePeer
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface MessageSendResult {
  id: number
  content: string
  recipient_id: number
  created_at: string
}

export function useMessages() {
  /** GET /messages/unread/count —— 角标轮询用静默口：失败不打 toast，下一轮自愈。 */
  const getUnreadMessageCount = () =>
    silentApiFetch<{ count: number }>('/messages/unread/count')

  /** POST /messages —— 正文走请求体，见文件头第 3 条。 */
  const sendPrivateMessage = (recipientId: number, content: string) =>
    apiFetch<MessageSendResult>('/messages', {
      method: 'POST',
      body: { recipient_id: recipientId, content }
    })

  /** PUT /messages/read-all/{user_id} —— 不打开会话直接清掉该对端的未读。 */
  const markConversationRead = (peerId: number) =>
    apiFetch<{ success: boolean }>(`/messages/read-all/${peerId}`, { method: 'PUT' })

  return {
    getUnreadMessageCount,
    sendPrivateMessage,
    markConversationRead
  }
}
