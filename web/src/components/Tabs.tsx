import React, { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import type { Tab } from '../types/models'
import { Tabs as TabsRoot, TabsList, TabsTrigger } from '@/components/ui/tabs'

interface TabsProps {
  tabs: Tab[]
  activeTab: string
}

const Tabs: React.FC<TabsProps> = ({ tabs, activeTab }) => {
  const navigate = useNavigate()

  const handleTabChange = useCallback(
    (value: string) => {
      if (value !== activeTab) {
        navigate(`/${value}`)
      }
    },
    [activeTab, navigate],
  )

  return (
    <TabsRoot
      value={activeTab}
      onValueChange={handleTabChange}
      className="w-full"
    >
      <TabsList className="flex w-full justify-start gap-1 overflow-x-auto overflow-y-hidden bg-muted p-1.5 md:flex-wrap md:gap-2 md:p-2">
        {tabs.map((tab) => (
          <TabsTrigger
            key={tab.id}
            value={tab.id}
            className="flex-shrink-0 gap-1.5 px-3 py-2 text-sm md:gap-2 md:px-4 md:text-base"
          >
            {tab.icon && <span aria-hidden="true">{tab.icon}</span>}
            <span>{tab.label}</span>
          </TabsTrigger>
        ))}
      </TabsList>
    </TabsRoot>
  )
}

export default Tabs
