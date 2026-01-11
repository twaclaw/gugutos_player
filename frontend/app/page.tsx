'use client'

import { useState } from 'react'
import { Tab } from '@headlessui/react'
import { motion } from 'framer-motion'
import useSWR from 'swr'
import { Music, BookOpen, Moon, Sun, CloudRain, Leaf, Snowflake, Sprout, Clock, Type, Flower2, Umbrella, Wind, ThermometerSnowflake, Mountain, Waves } from 'lucide-react'
import { cn } from '@/lib/utils'

const getBackendUrl = (path: string) => {
  if (!path) return '';
  if (path.startsWith('http')) return path;

  const configuredIp = process.env.NEXT_PUBLIC_SERVER_IP;
  if (configuredIp) {
    return `http://${configuredIp}:8000${path}`;
  }
  const hostname = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
  return `http://${hostname}:8000${path}`;
}

const fetcher = (url: string) => {
  return fetch(getBackendUrl(url), { cache: 'no-store' }).then((res) => {
    if (!res.ok) throw new Error('Network response was not ok')
    return res.json()
  })
}

const SeasonIcon = ({ season }: { season: number }) => {
  const iconSize = 48;
  switch (season) {
    case 1: // Spring
      return (
        <div className="flex gap-4">
          <Sprout size={iconSize} className="text-green-500" />
          <Flower2 size={iconSize} className="text-pink-400" />
          <CloudRain size={iconSize} className="text-blue-400" />
        </div>
      );
    case 2: // Summer
      return (
        <div className="flex gap-4">
          <Sun size={iconSize} className="text-yellow-500" />
          <Umbrella size={iconSize} className="text-red-400" />
          <Waves size={iconSize} className="text-blue-500" />
        </div>
      );
    case 3: // Autumn
      return (
        <div className="flex gap-4">
          <Leaf size={iconSize} className="text-orange-500" />
          <Wind size={iconSize} className="text-slate-400" />
          <CloudRain size={iconSize} className="text-gray-400" />
        </div>
      );
    case 4: // Winter
      return (
        <div className="flex gap-4">
          <Snowflake size={iconSize} className="text-blue-300" />
          <ThermometerSnowflake size={iconSize} className="text-blue-500" />
          <Mountain size={iconSize} className="text-slate-500" />
        </div>
      );
    default: return <Sun size={iconSize} className="text-yellow-500" />;
  }
}

export default function Home() {
  const [language, setLanguage] = useState<'ES' | 'LT' | 'EN' | 'DE'>('ES')
  const [allCaps, setAllCaps] = useState(true)

  const { data: tags, error, isLoading } = useSWR(`/list_server_tags?all_caps=${allCaps}`, fetcher, {
    revalidateOnFocus: true,
    refreshInterval: 5000
  })

  const { data: timeData } = useSWR(`/current_time?lang=${language}&all_caps=${allCaps}`, fetcher, {
    refreshInterval: 10000
  })

  const { data: currentTrack } = useSWR(`/current_track?all_caps=${allCaps}`, fetcher, {
    refreshInterval: 5000
  })

  if (error) console.error("SWR Error:", error);

  const safeTags = Array.isArray(tags) ? tags : [];

  const playTrack = async (tagId: string) => {
    try {
      await fetch(getBackendUrl(`/play/${tagId}`), { method: 'POST' })
    } catch (err) {
      console.error('Failed to play', err)
    }
  }

  const tabs = [
    { name: 'TOCAR MÚSICA', icon: Music, color: 'bg-kid-blue' },
    { name: '¿QUÉ MÚSICA ES?', icon: BookOpen, color: 'bg-kid-pink' },
    { name: '¿QUÉ HORA ES?', icon: Moon, color: 'bg-kid-purple' },
  ]

  return (
    <main className="h-screen bg-slate-50 p-1 flex flex-col overflow-hidden">
      <Tab.Group as="div" className="flex flex-col h-full">
        <Tab.List className="flex-none flex space-x-1 rounded-xl bg-white p-1 shadow-lg mb-2 z-10">
          {tabs.map((tab) => (
            <Tab
              key={tab.name}
              className={({ selected }) =>
                cn(
                  'w-full rounded-lg py-2 text-xs font-bold leading-5 transition-all duration-200 outline-none',
                  selected
                    ? `${tab.color} text-white shadow-md scale-105`
                    : 'text-slate-400 hover:bg-slate-100 hover:text-slate-600'
                )
              }
            >
              <div className="flex flex-col items-center gap-1">
                <tab.icon size={20} />
                <span className="text-center">{tab.name}</span>
              </div>
            </Tab>
          ))}
        </Tab.List>
        <Tab.Panels className="flex-1 overflow-hidden relative min-h-0">
          <Tab.Panel
            className="h-full overflow-y-auto space-y-4 pb-20"
          >
            <div className="flex justify-end px-2">
              <button
                onClick={() => setAllCaps(!allCaps)}
                className={cn(
                  "p-2 rounded-lg transition-colors flex items-center gap-2 text-sm font-bold",
                  allCaps ? "bg-kid-blue text-white" : "bg-slate-200 text-slate-600"
                )}
              >
                <Type size={20} />
                {allCaps ? "AA" : "Aa"}
              </button>
            </div>
            {isLoading ? (
               <div className="text-center p-10 text-slate-400 text-xl">Loading...</div>
            ) : error ? (
               <div className="text-center p-10 text-red-400 text-xl">Error loading tracks</div>
            ) : safeTags.length > 0 ? (
              safeTags.map((tag: any) => (
                <motion.button
                  key={tag.id}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => playTrack(tag.id)}
                  className="w-full bg-white rounded-2xl p-4 shadow-sm border-2 border-slate-100 flex items-center gap-6 text-left select-none"
                >
                  <div className="relative w-64 h-64 rounded-xl overflow-hidden bg-slate-200 flex-shrink-0">
                    {tag.image ? (
                      <img src={getBackendUrl(tag.image)} alt={tag.title} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-slate-400">
                        <Music size={96} />
                      </div>
                    )}
                  </div>
                  <div className="flex-1">
                    {/* font songs list in first tab */}
                    <h3 className="text-5xl font-black text-slate-800 leading-tight mb-2">
                      {tag.title}
                    </h3>
                  </div>
                </motion.button>
              ))
            ) : (
              <div className="text-center p-10 text-slate-400 text-xl">No tracks found</div>
            )}
          </Tab.Panel>
          <Tab.Panel className="flex flex-col items-center justify-center min-h-[50vh] space-y-4 p-4 relative">
            <div className="absolute top-0 right-0 flex gap-4">
              <button
                onClick={() => setAllCaps(!allCaps)}
                className={cn(
                  "p-2 rounded-lg transition-colors flex items-center gap-2 text-sm font-bold",
                  allCaps ? "bg-kid-blue text-white" : "bg-slate-200 text-slate-600"
                )}
              >
                <Type size={20} />
                {allCaps ? "AA" : "Aa"}
              </button>
            </div>

            {currentTrack && currentTrack.name ? (
              <>
                <div className="relative w-80 h-80 rounded-3xl overflow-hidden shadow-2xl ring-4 ring-white">
                  {currentTrack.image ? (
                    <img src={getBackendUrl(currentTrack.image)} alt={currentTrack.name} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full bg-slate-200 flex items-center justify-center text-slate-400">
                      <Music size={128} />
                    </div>
                  )}
                </div>

                <div className="text-center space-y-2 max-w-2xl">
                  <h2 className="text-3xl font-black text-slate-800 leading-tight">
                    {currentTrack.name}
                  </h2>
                  {currentTrack.artist && (
                    <p className="text-xl font-bold text-kid-purple">
                      {currentTrack.artist}
                    </p>
                  )}
                </div>
              </>
            ) : (
              <div className="text-center p-10 text-slate-400 text-xl font-bold">
                Nothing playing right now
              </div>
            )}
          </Tab.Panel>
          <Tab.Panel className="flex flex-col items-center justify-center min-h-[50vh] space-y-4 p-4 relative">
            <div className="absolute top-0 left-0 flex gap-4">
              <button
                onClick={() => setAllCaps(!allCaps)}
                className={cn(
                  "p-2 rounded-lg transition-colors flex items-center gap-2 text-sm font-bold",
                  allCaps ? "bg-kid-blue text-white" : "bg-slate-200 text-slate-600"
                )}
              >
                <Type size={20} />
                {allCaps ? "AA" : "Aa"}
              </button>
            </div>
            <div className="absolute top-0 right-0 flex gap-4">
              <button
                onClick={() => setLanguage('LT')}
                className={cn("text-4xl p-2 rounded-xl transition-all", language === 'LT' ? "bg-white shadow-lg scale-110 ring-2 ring-kid-blue/20" : "opacity-40 hover:opacity-100 grayscale")}
                title="Lietuviškai"
              >
                🇱🇹
              </button>
              <button
                onClick={() => setLanguage('ES')}
                className={cn("text-4xl p-2 rounded-xl transition-all", language === 'ES' ? "bg-white shadow-lg scale-110 ring-2 ring-kid-blue/20" : "opacity-40 hover:opacity-100 grayscale")}
                title="Español"
              >
                🇨🇴
              </button>
              <button
                onClick={() => setLanguage('EN')}
                className={cn("text-4xl p-2 rounded-xl transition-all", language === 'EN' ? "bg-white shadow-lg scale-110 ring-2 ring-kid-blue/20" : "opacity-40 hover:opacity-100 grayscale")}
                title="English"
              >
                🇬🇧
              </button>
              <button
                onClick={() => setLanguage('DE')}
                className={cn("text-4xl p-2 rounded-xl transition-all", language === 'DE' ? "bg-white shadow-lg scale-110 ring-2 ring-kid-blue/20" : "opacity-40 hover:opacity-100 grayscale")}
                title="Deutsch"
              >
                🇩🇪
              </button>
            </div>

            {timeData ? (
              <>
                <div className="flex flex-col items-center space-y-2">
                  <SeasonIcon season={timeData.season} />
                  <h2 className="text-2xl font-black text-slate-600 text-center tracking-wide">
                    {timeData.date}
                  </h2>
                </div>

                <div className="flex items-center gap-4 text-slate-800">
                  <Clock size={64} strokeWidth={2.5} />
                  <div className="text-[6rem] font-black leading-none tracking-tighter">
                    {timeData.time_number}
                  </div>
                </div>

                <div className="text-3xl font-black text-kid-purple text-center max-w-4xl leading-relaxed">
                  {timeData.time_str}
                </div>
              </>
            ) : (
              <div className="text-xl text-slate-400">Loading time...</div>
            )}
          </Tab.Panel>
        </Tab.Panels>
      </Tab.Group>
    </main>
  )
}
