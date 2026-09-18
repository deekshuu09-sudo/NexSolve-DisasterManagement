import { AnimatePresence, motion } from 'motion/react'

export type NavMenuItem = {
  label: string
  target: string
  menu?: Array<{
    title: string
    description: string
    target: string
  }>
}

type NavbarMenuProps = {
  items: NavMenuItem[]
  activeTab: string
  openLabel: string | null
  onOpenChange: (label: string | null) => void
  onNavigate: (target: string) => void
}

export function NavbarMenu({ items, activeTab, openLabel, onOpenChange, onNavigate }: NavbarMenuProps) {
  return (
    <nav className="topbar-nav" aria-label="Primary navigation">
      {items.map((item) => {
        const hasMenu = Boolean(item.menu?.length)
        const isItemActive =
          item.label === activeTab ||
          (hasMenu && item.menu!.some((m) =>
            (activeTab === 'Vulnerability' && m.target === 'vuln-step') ||
            (activeTab === 'Explainability' && m.target === 'xai-step') ||
            (activeTab === 'System Status' && (m.target === 'response-step' || m.target === 'status-step'))
          ))

        return (
          <div className="nav-item" key={item.label}>
            <button
              type="button"
              className={`nav-link ${isItemActive ? 'active' : ''}`}
              onClick={() => {
                if (!hasMenu) {
                  onNavigate(item.target)
                  return
                }

                onOpenChange(openLabel === item.label ? null : item.label)
              }}
              aria-expanded={openLabel === item.label}
            >
              {item.label}
              {hasMenu && <span className="caret" aria-hidden="true">▾</span>}
            </button>

            {hasMenu && (
              <AnimatePresence>
                {openLabel === item.label && (
                  <motion.div
                    className="nav-menu"
                    initial={{ opacity: 0, y: 6, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 4, scale: 0.98 }}
                    transition={{ duration: 0.15, ease: 'easeOut' }}
                  >
                    {item.menu!.map((entry) => (
                      <button
                        type="button"
                        key={entry.title}
                        onClick={() => {
                          onNavigate(entry.target)
                          onOpenChange(null)
                        }}
                      >
                        <b>{entry.title}</b>
                        <small>{entry.description}</small>
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            )}
          </div>
        )
      })}
    </nav>
  )
}
