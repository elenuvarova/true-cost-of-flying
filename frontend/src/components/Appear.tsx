import { useReveal } from '../lib/scroll'

export default function Appear({
  children,
  delay = 0,
  className = '',
  as = 'div',
}: {
  children: React.ReactNode
  delay?: number
  className?: string
  as?: any
}) {
  const ref = useReveal<HTMLElement>()
  const Tag = as as any
  return (
    <Tag ref={ref as any} className={`reveal ${className}`} style={{ transitionDelay: `${delay}ms` }}>
      {children}
    </Tag>
  )
}
