import { useEffect, useState } from "react";
import { Sun, Cloud, CloudRain, CloudSnow, CloudLightning, CloudFog, CloudSun, Wind, Droplets } from "lucide-react";
import { api } from "../../lib/api";

const CODES = [
  [[0], Sun, "Vedro"], [[1, 2], CloudSun, "Djelimično oblačno"], [[3], Cloud, "Oblačno"], [[45, 48], CloudFog, "Magla"],
  [[51, 53, 55, 61, 63, 65, 80, 81, 82], CloudRain, "Kiša"], [[71, 73, 75, 77, 85, 86], CloudSnow, "Snijeg"], [[95, 96, 99], CloudLightning, "Grmljavina"],
];
export const wx = (code) => CODES.find(([c]) => c.includes(code)) || CODES[2];
const DAYS = ["Ned", "Pon", "Uto", "Sri", "Čet", "Pet", "Sub"];

let cached = null;
export function useWeather() {
  const [w, setW] = useState(cached);
  useEffect(() => {
    if (!cached) api.get("/public/weather").then((r) => { cached = r.data; setW(r.data); }).catch(() => {});
  }, []);
  return w;
}

export function WeatherWidget() {
  const w = useWeather();
  if (!w?.current) return null;
  const [, Icon, label] = wx(w.current.weather_code);
  return (
    <section className="relative overflow-hidden rounded-lg p-5 text-white bg-gradient-to-br from-ccn-navy to-[#0E3A5C]" data-testid="weather-widget">
      <div className="absolute -right-10 -top-10 w-40 h-40 rounded-full bg-ccn-gold/20 blur-2xl" />
      <h2 className="text-xs font-bold uppercase tracking-[0.18em] text-white/60">Vrijeme u Cazinu</h2>
      <div className="flex items-center gap-4 mt-3">
        <Icon className="w-12 h-12 text-ccn-gold" />
        <div>
          <p className="text-5xl font-bold tracking-tight" data-testid="weather-temp">{Math.round(w.current.temperature_2m)}°</p>
          <p className="text-sm text-white/75">{label}</p>
        </div>
      </div>
      <div className="flex gap-4 text-xs text-white/60 mt-3">
        <span className="flex items-center gap-1"><Wind className="w-3.5 h-3.5" />{Math.round(w.current.wind_speed_10m)} km/h</span>
        <span className="flex items-center gap-1"><Droplets className="w-3.5 h-3.5" />{w.current.relative_humidity_2m}%</span>
      </div>
      <div className="grid grid-cols-5 gap-1 mt-4 pt-4 border-t border-white/15 text-center relative">
        {w.daily.time.map((d, i) => {
          const [, DI] = wx(w.daily.weather_code[i]);
          return (
            <div key={d} className="text-xs">
              <p className="text-white/55">{DAYS[new Date(d).getDay()]}</p>
              <DI className="w-5 h-5 mx-auto my-1 text-ccn-teal" />
              <p className="font-semibold">{Math.round(w.daily.temperature_2m_max[i])}°</p>
              <p className="text-white/45">{Math.round(w.daily.temperature_2m_min[i])}°</p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
