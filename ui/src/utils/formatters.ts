export const formatDate = (iso?: string | null) => {
  if (!iso) return '-'
  return new Date(iso).toLocaleString()
}

export const truncate = (str: string, max = 60) => {
  if (str.length <= max) return str
  return str.slice(0, max) + '...'
}

export const repoNameFromUrl = (url: string) => {
  return url.split('/').pop()?.replace('.git', '') || url
}
