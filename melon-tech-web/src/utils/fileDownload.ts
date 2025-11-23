export function triggerFileDownload(href: string, downloadName?: string) {
  if (!href) return

  const link = document.createElement('a')
  link.href = href
  if (downloadName !== undefined) {
    // 为空字符串也显式设置，意味着“使用后端 Content-Disposition 的文件名”
    link.download = downloadName || ''
  }
  link.style.display = 'none'
  document.body.appendChild(link)
  try {
    link.click()
  } finally {
    document.body.removeChild(link)
  }
}

