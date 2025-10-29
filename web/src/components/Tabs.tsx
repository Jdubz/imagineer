import React from 'react'
import { Link } from 'react-router-dom'
import type { Tab } from '../types/models'
import '../styles/Tabs.css'

interface TabsProps {
  tabs: Tab[]
  activeTab: string
}

const Tabs: React.FC<TabsProps> = ({ tabs, activeTab }) => {
  return (
    <div className="tabs">
      {tabs.map((tab) => (
        <Link
          key={tab.id}
          to={`/${tab.id}`}
          className={`tab ${activeTab === tab.id ? 'active' : ''}`}
        >
          {tab.icon && <span className="tab-icon">{tab.icon}</span>}
          <span className="tab-label">{tab.label}</span>
        </Link>
      ))}
    </div>
  )
}

export default Tabs
