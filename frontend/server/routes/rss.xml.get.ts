export default defineEventHandler(async (event) => {
  const runtime = useRuntimeConfig(event)
  const pub = runtime.public || {}
  const apiBase = pub.apiBase as string | undefined || '/api'
  const backendHost = process.env.BACKEND_HOST || '127.0.0.1'
  const backendPort = process.env.BACKEND_PORT || '8000'

  let target: string
  if (apiBase.startsWith('http://') || apiBase.startsWith('https://')) {
    target = `${apiBase.replace(/\/$/, '')}/blog/rss`
  } else {
    target = `http://${backendHost}:${backendPort}/api/blog/rss`
  }

  try {
    const res = await $fetch.raw(target, {
      headers: { accept: 'application/rss+xml' },
      redirect: 'follow'
    })
    setHeader(event, 'content-type', 'application/rss+xml; charset=utf-8')
    setHeader(event, 'cache-control', 'public, max-age=1800, s-maxage=1800')
    return res._data ?? res.body
  } catch (err) {
    throw createError({
      statusCode: 502,
      statusMessage: 'RSS upstream unavailable',
      data: String(err)
    })
  }
})
