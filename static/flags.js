// Переключатель тёмной темы: тоглит класс dark на <html> и запоминает выбор в localStorage
function toggleTheme() {
    document.documentElement.classList.toggle('dark');
    localStorage.theme = document.documentElement.classList.contains('dark') ? 'dark' : 'light';
    // Если сейчас крутится ротация (не страница конкретной страны) — сразу подбираем
    // флаг, подходящий под новую тему, не дожидаясь следующего тика ротации
    if (typeof pickFlagForTheme === 'function') pickFlagForTheme();
}

// Функционал для рандомных цветов флагов в заголовке сайта

// Список флагов с цветами для трёх частей названия: t=Travel, p=Pin, h=Hunt
const flags = [
    // Европа
    { name: "france",        t: "#002395", p: "#FFFFFF", h: "#ED2939" },
    { name: "germany",       t: "#000000", p: "#DD0000", h: "#FFCE00" },
    { name: "italy",         t: "#009246", p: "#FFFFFF", h: "#CE2B37" },
    { name: "netherlands",   t: "#AE1C28", p: "#FFFFFF", h: "#21468B" },
    { name: "russia",        t: "#FFFFFF", p: "#0039A6", h: "#D52B1E" },
    { name: "hungary",       t: "#CE2939", p: "#FFFFFF", h: "#477050" },
    { name: "spain",         t: "#AA151B", p: "#F1BF00", h: "#AA151B" },
    { name: "romania",       t: "#002B7F", p: "#FCD116", h: "#CE1126" },
    { name: "belgium",       t: "#000000", p: "#FAE042", h: "#EF3340" },
    { name: "lithuania",     t: "#FDB913", p: "#006A44", h: "#C1272D" },
    { name: "estonia",       t: "#0072CE", p: "#000000", h: "#FFFFFF" },
    { name: "switzerland",   t: "#FF0000", p: "#FFFFFF", h: "#FF0000" },
    { name: "bosnia-and-herzegovina", t: "#002395", p: "#FFFFFF", h: "#FFCE00" },
    { name: "sweden",        t: "#006AA7", p: "#FECC02", h: "#006AA7" },
    { name: "luxembourg",    t: "#EF3340", p: "#FFFFFF", h: "#00A3E0" },
    { name: "greece",        t: "#0D5EAF", p: "#FFFFFF", h: "#0D5EAF" },
    { name: "bulgaria",      t: "#FFFFFF", p: "#00966E", h: "#D62612" },
    { name: "serbia",        t: "#C6363C", p: "#0C4076", h: "#FFFFFF" },
    { name: "liechtenstein", t: "#002B7F", p: "#FFD700", h: "#CE1126" },
    { name: "cyprus",        t: "#FFFFFF", p: "#D17D00", h: "#4E7A3A" },
    // Азия
    { name: "india",         t: "#FF9933", p: "#FFFFFF", h: "#138808" },
    { name: "kazakhstan",    t: "#00AFCA", p: "#FFDD00", h: "#00AFCA" },
    { name: "japan",         t: "#FFFFFF", p: "#BC002D", h: "#FFFFFF" },
    { name: "uzbekistan",    t: "#009FE3", p: "#FFFFFF", h: "#1EB53A" },
    { name: "kyrgyzstan",    t: "#E8112D", p: "#FFE800", h: "#E8112D" },
    { name: "bhutan",        t: "#FFD700", p: "#FFFFFF", h: "#FF8000" },
    { name: "china",         t: "#FFDE00", p: "#DE2910", h: "#DE2910" },
    // Америки и Карибы
    { name: "united-states", t: "#B22234", p: "#FFFFFF", h: "#3C3B6E" },
    { name: "colombia",      t: "#FCD116", p: "#003087", h: "#CE1126" },
    { name: "brazil",        t: "#009C3B", p: "#FFDF00", h: "#009C3B" },
    { name: "argentina",     t: "#74ACDF", p: "#FFFFFF", h: "#74ACDF" },
    { name: "jamaica",       t: "#000000", p: "#00A551", h: "#FED100" },
    { name: "bahamas",       t: "#00778B", p: "#FFC72C", h: "#00778B" },
    { name: "barbados",      t: "#00267F", p: "#FFC726", h: "#00267F" },
    // Ближний восток и рядом
    { name: "turkey",        t: "#E30A17", p: "#FFFFFF", h: "#E30A17" },
    { name: "saudi-arabia",  t: "#006C35", p: "#FFFFFF", h: "#006C35" },
    { name: "qatar",         t: "#FFFFFF", p: "#8D1B3D", h: "#8D1B3D" },
    { name: "armenia",       t: "#D90012", p: "#0033A0", h: "#F2A800" },
    // Африка
    { name: "south-africa",  t: "#007A4D", p: "#FFB81C", h: "#001489" },
    { name: "kenya",         t: "#006600", p: "#CC0001", h: "#000000" },
    { name: "ethiopia",      t: "#078930", p: "#FCDD09", h: "#DA121A" },
    { name: "morocco",       t: "#C1272D", p: "#006233", h: "#C1272D" },
    { name: "tanzania",      t: "#1EB53A", p: "#FCD116", h: "#00A3DD" },
];

// Дополнительные флаги — только для окраски страниц стран, не участвуют в ротации
const extraFlags = [
    // Европа
    { name: "albania",              t: "#E41E20", p: "#000000", h: "#E41E20" },
    { name: "andorra",              t: "#003DA5", p: "#FEDF00", h: "#C7092C" },
    { name: "croatia",              t: "#D4212B", p: "#FFFFFF", h: "#1D1DA8" },
    { name: "monaco",               t: "#CE1126", p: "#FFFFFF", h: "#CE1126" },
    { name: "slovenia",             t: "#003DA5", p: "#FFFFFF", h: "#CE1126" },
    { name: "austria",              t: "#ED2939", p: "#FFFFFF", h: "#ED2939" },
    { name: "czechia",              t: "#D7141A", p: "#FFFFFF", h: "#11457E" },
    { name: "denmark",              t: "#C60C30", p: "#FFFFFF", h: "#C60C30" },
    { name: "finland",              t: "#003580", p: "#FFFFFF", h: "#003580" },
    { name: "norway",               t: "#EF2B2D", p: "#FFFFFF", h: "#002868" },
    { name: "poland",               t: "#FFFFFF", p: "#DC143C", h: "#FFFFFF" },
    { name: "portugal",             t: "#006600", p: "#FF0000", h: "#006600" },
    { name: "slovakia",             t: "#FFFFFF", p: "#0B4EA2", h: "#EE1C25" },
    { name: "ukraine",              t: "#005BBB", p: "#FFD500", h: "#005BBB" },
    { name: "ireland",              t: "#169B62", p: "#FFFFFF", h: "#FF883E" },
    { name: "georgia",              t: "#FFFFFF", p: "#FF0000", h: "#FFFFFF" },
    { name: "iceland",              t: "#003897", p: "#FFFFFF", h: "#D72828" },
    { name: "latvia",               t: "#9E3039", p: "#FFFFFF", h: "#9E3039" },
    { name: "malta",                t: "#FFFFFF", p: "#CF142B", h: "#CF142B" },
    { name: "north-macedonia",      t: "#CE2028", p: "#F7DB17", h: "#CE2028" },
    { name: "north-cyprus",         t: "#FFFFFF", p: "#E30A17", h: "#FFFFFF" },
    { name: "south-ossetia",        t: "#FFFFFF", p: "#E30A17", h: "#FFCC00" },
    // Азия
    { name: "cambodia",             t: "#032EA1", p: "#E00025", h: "#032EA1" },
    { name: "hong-kong",            t: "#DE2910", p: "#FFFFFF", h: "#DE2910" },
    { name: "indonesia",            t: "#CE1126", p: "#FFFFFF", h: "#CE1126" },
    { name: "macau",                t: "#00785E", p: "#FFFFFF", h: "#00785E" },
    { name: "malaysia",             t: "#CC0001", p: "#FFFFFF", h: "#003399" },
    { name: "mongolia",             t: "#C4272F", p: "#015197", h: "#C4272F" },
    { name: "singapore",            t: "#EF3340", p: "#FFFFFF", h: "#EF3340" },
    { name: "tajikistan",           t: "#CC0000", p: "#FFFFFF", h: "#009A44" },
    { name: "thailand",             t: "#A51931", p: "#FFFFFF", h: "#2D2A4A" },
    { name: "vietnam",              t: "#DA251D", p: "#FFCD00", h: "#DA251D" },
    { name: "south-korea",          t: "#FFFFFF", p: "#CD2E3A", h: "#003478" },
    { name: "taiwan",               t: "#FE0000", p: "#FFFFFF", h: "#000095" },
    { name: "myanmar",              t: "#FECB00", p: "#34B233", h: "#EA2839" },
    { name: "philippines",          t: "#0038A8", p: "#FFFFFF", h: "#CE1126" },
    { name: "laos",                 t: "#CE1126", p: "#FFFFFF", h: "#002868" },
    { name: "nepal",                t: "#003893", p: "#FFFFFF", h: "#DC143C" },
    { name: "sri-lanka",            t: "#8D153A", p: "#FF7722", h: "#006400" },
    { name: "pakistan",             t: "#01411C", p: "#FFFFFF", h: "#01411C" },
    { name: "bangladesh",           t: "#006A4E", p: "#F42A41", h: "#006A4E" },
    { name: "iran",                 t: "#239F40", p: "#FFFFFF", h: "#DA0000" },
    { name: "iraq",                 t: "#CE1126", p: "#FFFFFF", h: "#007A3D" },
    { name: "israel",               t: "#FFFFFF", p: "#0038B8", h: "#FFFFFF" },
    { name: "jordan",               t: "#007A3D", p: "#FFFFFF", h: "#000000" },
    { name: "kuwait",               t: "#007A3D", p: "#FFFFFF", h: "#CE1126" },
    { name: "oman",                 t: "#DB161B", p: "#FFFFFF", h: "#008000" },
    { name: "uae",                  t: "#00732F", p: "#FFFFFF", h: "#FF0000" },
    { name: "azerbaijan",           t: "#0092BC", p: "#ED2939", h: "#3F9C35" },
    { name: "afghanistan",          t: "#000000", p: "#FFFFFF", h: "#007A36" },
    // Африка
    { name: "nigeria",              t: "#008751", p: "#FFFFFF", h: "#008751" },
    { name: "ghana",                t: "#006B3F", p: "#FCD116", h: "#CE1126" },
    { name: "egypt",                t: "#CE1126", p: "#FFFFFF", h: "#000000" },
    { name: "senegal",              t: "#00853F", p: "#FDEF42", h: "#E31B23" },
    { name: "algeria",              t: "#006233", p: "#FFFFFF", h: "#D21034" },
    { name: "tunisia",              t: "#E70013", p: "#FFFFFF", h: "#E70013" },
    { name: "cameroon",             t: "#007A5E", p: "#CE1126", h: "#FCD116" },
    { name: "ivory-coast",          t: "#F77F00", p: "#FFFFFF", h: "#009A44" },
    { name: "rwanda",               t: "#20603D", p: "#FAD201", h: "#20A0D6" },
    { name: "uganda",               t: "#000000", p: "#FCDC04", h: "#DE3908" },
    { name: "zimbabwe",             t: "#006400", p: "#FFD200", h: "#D30000" },
    { name: "zambia",               t: "#198A00", p: "#EF7D00", h: "#000000" },
    { name: "mozambique",           t: "#009A44", p: "#FCF951", h: "#CE1126" },
    // Латинская Америка и Карибы
    { name: "mexico",               t: "#006847", p: "#FFFFFF", h: "#CE1126" },
    { name: "peru",                 t: "#D91023", p: "#FFFFFF", h: "#D91023" },
    { name: "chile",                t: "#D52B1E", p: "#FFFFFF", h: "#002D62" },
    { name: "uruguay",              t: "#FFFFFF", p: "#5EB6E4", h: "#FFFFFF" },
    { name: "venezuela",            t: "#CF142B", p: "#00247D", h: "#FCD116" },
    { name: "ecuador",              t: "#FFD100", p: "#0033A0", h: "#ED1C24" },
    { name: "bolivia",              t: "#D52B1E", p: "#F4E400", h: "#007A3D" },
    { name: "paraguay",             t: "#D52B1E", p: "#FFFFFF", h: "#0038A8" },
    { name: "panama",               t: "#FFFFFF", p: "#D21034", h: "#003580" },
    { name: "costa-rica",           t: "#002B7F", p: "#FFFFFF", h: "#CE1126" },
    { name: "cuba",                 t: "#002A8F", p: "#FFFFFF", h: "#CC0001" },
    { name: "haiti",                t: "#00209F", p: "#D21034", h: "#00209F" },
    { name: "dominican-republic",   t: "#002D62", p: "#FFFFFF", h: "#CE1126" },
    { name: "trinidad-and-tobago",  t: "#CE1126", p: "#000000", h: "#FFFFFF" },
    // Океания
    { name: "australia",            t: "#00008B", p: "#FFFFFF", h: "#FF0000" },
    { name: "new-zealand",          t: "#00247D", p: "#FFFFFF", h: "#CC142B" },
    { name: "fiji",                 t: "#68BFE5", p: "#FFFFFF", h: "#003087" },
    { name: "papua-new-guinea",     t: "#000000", p: "#CE1126", h: "#FCD116" },
];

// Полный каталог флагов (ротация + дополнительные) — используется для поиска цвета страницы страны
const flagCatalog = [...flags, ...extraFlags];

// Заполняется внутри DOMContentLoaded (только на страницах с ротацией) —
// вызывается из toggleTheme(), чтобы сразу подобрать флаг под новую тему
let pickFlagForTheme = null;

// Считает относительную яркость цвета (0 = чёрный, 1 = белый)
function getLuminance(hex) {
    const r = parseInt(hex.slice(1, 3), 16) / 255;
    const g = parseInt(hex.slice(3, 5), 16) / 255;
    const b = parseInt(hex.slice(5, 7), 16) / 255;
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

// Средняя яркость трёх букв флага — по ней делим флаги на "тёмные" и "светлые"
function avgFlagLuminance(flag) {
    return (getLuminance(flag.t) + getLuminance(flag.p) + getLuminance(flag.h)) / 3;
}

// Пул флагов для ротации под текущую тему:
// на светлой теме крутим только тёмные флаги, на тёмной — только светлые
// (страницы конкретных стран это правило не затрагивает — там флаг показывается как есть)
function rotationPool() {
    const isDark = document.documentElement.classList.contains('dark');
    const pool = flags.filter(f => isDark ? avgFlagLuminance(f) >= 0.5 : avgFlagLuminance(f) < 0.5);
    return pool.length ? pool : flags; // подстраховка на случай пустого пула
}

// Применяет цвета выбранного флага к буквам заголовка
// Для белых цветов добавляет тень чтобы текст был виден на светлом фоне
function applyFlag(flag) {
    const shadow = "0 1px 3px rgba(0,0,0,0.45)";
    ['t', 'p', 'h'].forEach((part, index) => {
        setTimeout(() => {
            const el = document.querySelector('.logo-' + part);
            el.style.color = flag[part];
            el.style.textShadow = (flag[part] === '#FFFFFF' || flag[part] === '#F0F0F0') ? shadow : '';
        }, index * 80); // волна: 0ms → 80ms → 160ms
    });
}

document.addEventListener('DOMContentLoaded', function() {
    let lastIndex = -1;

    // Применяет флаг мгновенно, без анимации (для первоначальной загрузки)
    function applyFlagInstant(flag) {
        const shadow = "0 1px 3px rgba(0,0,0,0.45)";
        ['t', 'p', 'h'].forEach(part => {
            const el = document.querySelector('.logo-' + part);
            el.style.transition = 'none';
            el.style.color = flag[part];
            el.style.textShadow = (flag[part] === '#FFFFFF' || flag[part] === '#F0F0F0') ? shadow : '';
        });
        // Возвращаем transition после применения цвета
        setTimeout(() => {
            ['t', 'p', 'h'].forEach(part => {
                document.querySelector('.logo-' + part).style.transition = '';
            });
        }, 50);
    }

    function nextFlag() {
        const pool = rotationPool();
        let index;
        do {
            index = Math.floor(Math.random() * pool.length);
        } while (index === lastIndex && pool.length > 1);
        lastIndex = index;
        applyFlag(pool[index]);
    }

    // Если открыта страница страны — показать её флаг как есть, без фильтра по теме
    if (pageCountry) {
        const countryFlag = flagCatalog.find(f => f.name === pageCountry);
        if (countryFlag) {
            applyFlagInstant(countryFlag);
            return; // не запускаем setInterval
        }
    }

    // На остальных страницах — подбираем флаг под текущую тему и крутим каждые 4 секунды
    const initialPool = rotationPool();
    applyFlagInstant(initialPool[Math.floor(Math.random() * initialPool.length)]);
    lastIndex = -1;
    setInterval(nextFlag, 4000);

    // Позволяет toggleTheme() мгновенно подобрать подходящий флаг при смене темы
    pickFlagForTheme = function() {
        const pool = rotationPool();
        const index = Math.floor(Math.random() * pool.length);
        lastIndex = index;
        applyFlagInstant(pool[index]);
    };
});
