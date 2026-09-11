import { AnimatePresence, motion } from 'motion/react'
import { useState } from 'react'

type MenuItem = [string, string, string]

type NavItem = {
  label: string
  target: string
  menu?: MenuItem[]
}

type NavbarMenuProps = {
  items: NavItem[]
  activeStep: number
  sectionIds: string[]
  onNavigate: (target: string) => void
}

export default function NavbarMenu({
  items,
  activeStep,
  sectionIds,
  onNavigate,
}: NavbarMenuProps) {
  const [active, setActive] = useState<string | null>(null)

  const isActive = (item: NavItem) => {
    if (item.target === sectionIds[activeStep]) return true

    return item.menu?.some(
      ([, , target]) => target === sectionIds[activeStep],
    )
  }

  return (
    <nav
      className="aceternity-navbar"
      onMouseLeave={() => setActive(null)}
    >
      {items.map((item) => (
        <div
          key={item.label}
          className="aceternity-nav-item"
          onMouseEnter={() => {
            if (item.menu) setActive(item.label)
            else setActive(null)
          }}
        >
          <button
            className={`aceternity-nav-trigger ${
              isActive(item) ? 'active' : ''
            }`}
            onClick={() => {
              if (!item.menu) {
                onNavigate(item.target)
                setActive(null)
              }
            }}
          >
            {item.label}

            {item.menu && (
              <span
                className={`nav-chevron ${
                  active === item.label ? 'open' : ''
                }`}
              >
                ↓
              </span>
            )}
          </button>

          <AnimatePresence>
            {active === item.label && item.menu && (
              <motion.div
                initial={{
                  opacity: 0,
                  y: 8,
                  scale: 0.96,
                }}
                animate={{
                  opacity: 1,
                  y: 0,
                  scale: 1,
                }}
                exit={{
                  opacity: 0,
                  y: 6,
                  scale: 0.97,
                }}
                transition={{
                  duration: 0.18,
                  ease: 'easeOut',
                }}
                className="aceternity-nav-dropdown"
              >
                <div className="aceternity-dropdown-inner">
                  {item.menu.map(([title, description, target]) => (
                    <motion.button
                      key={title}
                      whileHover={{ x: 3 }}
                      transition={{ duration: 0.15 }}
                      className={`aceternity-menu-card ${
                        sectionIds[activeStep] === target ? 'selected' : ''
                      }`}
                      onClick={() => {
                        onNavigate(target)
                        setActive(null)
                      }}
                    >
                      <span className="aceternity-menu-title">
                        {title}
                      </span>

                      <span className="aceternity-menu-description">
                        {description}
                      </span>
                    </motion.button>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      ))}
    </nav>
  )
}