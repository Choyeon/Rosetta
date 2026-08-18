export default defineEventHandler(async (event) => {
  const runtime = useRuntimeConfig(event)
  const pub = runtime.public || {}
  const apiBase = pub.apiBase as string | undefined || '/api'
  const backendHost = process.env.BACKEND_HOST || '127.0.0.1'
  const backendPort = process.env.BACKEND_PORT || '8000'

  let target: string
  if (apiBase.startsWith('http://') || apiBase.startsWith('https://')) {
    target = `${apiBase.replace(/\/$/, '')}/seo/robots.txt`
  } else {
    target = `http://${backendHost}:${backendPort}/api/seo/robots.txt`
  }

  try {
    const res = await $fetch.raw(target, {
      headers: { accept: 'text/plain' },
      redirect: 'follow'
    })
    setHeader(event, 'content-type', 'text/plain; charset=utf-8')
    setHeader(event, 'cache-control', 'public, max-age=3600, s-maxage=3600')
    return res._data ?? res.body
  } catch (err) {
    throw createError({
      statusCode: 502,
      statusMessage: 'robots.txt upstream unavailable',
      data: String(err)
    })
  }
})
