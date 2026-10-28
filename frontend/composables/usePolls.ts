/**
 * 全站投票：后端 API 挂在 /api/voting 前缀（backend/main.py::include_router）。
 * 前端 baseURL 已含 /api，所以调用路径写成 `/voting/polls` 而不是 `/api/voting/polls`。
 *
 * 说明：
 * - `Poll.post_id` 是绑定文章：null = 全站投票（挂在每篇文章下方），非 null = 只出现在这一篇。
 *   前台按文章取投票时必须带 `post_id`，否则别文章的专属投票会串到本页来。
 * - 匿名请求在 backend/api/voting.py::cast_vote 里没有 IP/user 唯一约束，重复提交会静默累加。
 *   为挡常见误操作，前端在 localStorage 记 `rosetta:voted-polls` 集合，命中即隐藏投票控件、
 *   直接显示结果（show_results 关掉时则显示"感谢参与"）。这不构成防刷，只避免用户手滑多点。
 * - 已登录用户重复投票：后端返回 409，前端提示"您已参与过该投票"。
 */
import { apiFetch } from '~~/composables/useApi'

export interface PollChoice {
  id: number
  text: string
  order: number
  votes_count: number | null
}

export interface Poll {
  id: number
  title: string
  description: string | null
  /** 绑定文章；null = 全站投票 */
  post_id: number | null
  is_active: boolean
  allow_multiple: boolean
  show_results: boolean
  choices: PollChoice[]
  total_votes: number
  created_at: string
}

export interface PollsListResponse {
  items: Poll[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

const VOTED_STORAGE_KEY = 'rosetta:voted-polls'

/** 只在客户端读；SSR 返回空集合，避免 hydration mismatch。 */
export function readVotedPollIds(): Set<number> {
  if (!import.meta.client || typeof localStorage === 'undefined') return new Set()
  try {
    const raw = localStorage.getItem(VOTED_STORAGE_KEY)
    if (!raw) return new Set()
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return new Set()
    return new Set(parsed.filter((x): x is number => typeof x === 'number'))
  } catch {
    return new Set()
  }
}

function markVoted(pollId: number) {
  if (!import.meta.client || typeof localStorage === 'undefined') return
  const set = readVotedPollIds()
  set.add(pollId)
  try {
    localStorage.setItem(VOTED_STORAGE_KEY, JSON.stringify([...set]))
  } catch {
    // 隐私模式 / 配额满时静默；不阻断投票成功反馈。
  }
}

export function usePolls() {
  /**
   * 拉取活动中的投票（首屏 MVP 只取前 5 条，够用）。
   * 传 `postId` 时只要「这一篇的专属投票 + 全站投票」；不传则维持全站口径。
   */
  const fetchActivePolls = async (limit = 5, postId?: number | null): Promise<Poll[]> => {
    try {
      const res = await apiFetch<PollsListResponse>(
        '/voting/polls',
        {
          query: {
            is_active: 'true',
            page: '1',
            page_size: String(limit),
            ...(postId && postId > 0 ? { post_id: String(postId) } : {})
          },
          silentToast: true
        }
      )
      // 后端 response_model 是 PaginatedResponse，字段直接在顶层。
      const items = (res as unknown as PollsListResponse)?.items
      return Array.isArray(items) ? items : []
    } catch {
      return []
    }
  }

  /**
   * 后台用：不带 is_active 过滤、失败要报（走 apiFetch 默认 toast）。
   * 与 fetchActivePolls 分开是因为后者必须"没有投票就不打扰访客"，
   * 而后台把故障咽成空列表会让管理员以为投票被删光了。
   */
  const fetchAllPolls = async (limit = 100): Promise<Poll[]> => {
    const res = await apiFetch<PollsListResponse>(
      '/voting/polls',
      { query: { page: '1', page_size: String(limit) } }
    )
    const items = (res as unknown as PollsListResponse)?.items
    return Array.isArray(items) ? items : []
  }

  /** POST /voting/polls（PollCreate：title + choices: string[]，另带绑定文章与三个开关）。 */
  const createPoll = async (payload: {
    title: string
    description?: string | null
    post_id?: number | null
    is_active: boolean
    allow_multiple: boolean
    show_results: boolean
    choices: string[]
  }): Promise<Poll> =>
    apiFetch<Poll>('/voting/polls', { method: 'POST', body: payload })

  /**
   * PUT /voting/polls/{id}（PollUpdate：只提交要改的键，缺省键保持原值）。
   * 选项不在这里改——每个选项 id 上挂着票数，后端也不接受 choices。
   */
  const updatePoll = async (
    pollId: number,
    payload: {
      title?: string
      description?: string | null
      post_id?: number | null
      is_active?: boolean
      allow_multiple?: boolean
      show_results?: boolean
    }
  ): Promise<Poll> =>
    apiFetch<Poll>(`/voting/polls/${pollId}`, { method: 'PUT', body: payload })

  const deletePoll = async (pollId: number): Promise<unknown> =>
    apiFetch<unknown>(`/voting/polls/${pollId}`, { method: 'DELETE' })

  /**
   * 提交投票。返回 'ok' | 'duplicate' | 'closed' | 'error'，由调用方决定 UI 反应。
   * 后端约定：409 = 已登录重复；400 = 已结束 / 单选塞多选 / 选项 id 非法；其余按通用错误处理。
   */
  const vote = async (pollId: number, choiceIds: number[]): Promise<'ok' | 'duplicate' | 'closed' | 'error'> => {
    try {
      await apiFetch(
        `/voting/polls/${pollId}/vote`,
        { method: 'POST', body: { choice_ids: choiceIds }, silentToast: true }
      )
      markVoted(pollId)
      return 'ok'
    } catch (e) {
      const status = (e as { status?: number })?.status
      if (status === 409) {
        markVoted(pollId)
        return 'duplicate'
      }
      if (status === 400) return 'closed'
      return 'error'
    }
  }

  return {
    fetchActivePolls,
    fetchAllPolls,
    createPoll,
    updatePoll,
    deletePoll,
    vote,
    readVotedPollIds
  }
}
