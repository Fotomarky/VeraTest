/**
 * Minimal i18n for the I Ching Oracle.
 * Strategy: The Sage prompt already instructs Gemini to reply in the user's question language.
 * This file handles all static UI strings so the shell matches too.
 *
 * We auto-detect the browser/OS locale and fall back to English.
 * Adding a new language = add one object to TRANSLATIONS.
 */

export type Locale = 'en' | 'it' | 'es' | 'fr' | 'de' | 'pt' | 'zh' | 'ja';

export interface Strings {
  appTitle: string;
  appSubtitle: string;
  inputPlaceholder: string;
  castButton: string;
  castHint: string;
  castManualProgress: (n: number) => string;
  readingComplete: string;
  consultingWisdom: string;
  sageUnreachable: string;
  sageGreeting: string;
  suggestedQuestions: string[];
  aboutTitle: string;
  aboutP1: string;
  aboutP2: string;
  aboutQuote: string;
  followUpSuggestions: string[];
  yangLabel: string;
  yinLabel: string;
  onboardingNamePrompt: string;
  onboardingAgePlaceholder: string;
  onboardingAgePrompt: string;
  onboardingNext: string;
  welcomeBack: (name: string) => string;
}

const TRANSLATIONS: Record<Locale, Strings> = {
  en: {
    appTitle: 'The I Ching Oracle',
    appSubtitle: 'What does your heart seek?',
    inputPlaceholder: 'Ask the oracle…',
    castButton: 'Cast the coins',
    castHint: '(or tap the coins to cast manually)',
    castManualProgress: (n) => `Cast manually (${n}/6)`,
    readingComplete: 'Reading Complete',
    consultingWisdom: 'Consulting the ancient wisdom…',
    sageUnreachable: 'The sage could not be reached at this moment.',
    sageGreeting: 'Welcome, traveler. What does your heart seek?',
    suggestedQuestions: [
      'What is my path forward?',
      'How should I handle this conflict?',
      'What do I need to focus on today?',
    ],
    aboutTitle: 'The Book of Changes',
    aboutP1: 'For over 3,000 years, emperors, generals, and sages have turned to the I Ching not to see the future, but to understand the present.',
    aboutP2: 'It is the world\'s oldest binary system — a mirror reflecting the invisible forces shaping your life right now. By casting the coins, you tap into the continuous, ancient flow of Yin and Yang, uncovering the hidden dynamics of your situation.',
    aboutQuote: '"The Sage does not tell you what to do; he reveals what is."',
    followUpSuggestions: ['What does the changing line mean?', 'Give me a practice for today', 'Ask another question'],
    yangLabel: 'Yang ☰',
    yinLabel: 'Yin ☷',
    onboardingNamePrompt: 'What is your name, seeker?',
    onboardingAgePlaceholder: 'Your age',
    onboardingAgePrompt: 'How many seasons have you lived?',
    onboardingNext: 'Continue →',
    welcomeBack: (name) => `Welcome back, ${name}.`,
  },
  it: {
    appTitle: "L'Oracolo dell'I Ching",
    appSubtitle: 'Cosa cerca il tuo cuore?',
    inputPlaceholder: "Chiedi all'oracolo…",
    castButton: 'Lancia le monete',
    castHint: '(o tocca le monete per lanciare manualmente)',
    castManualProgress: (n) => `Lancio manuale (${n}/6)`,
    readingComplete: 'Lettura Completata',
    consultingWisdom: 'Consultando la saggezza antica…',
    sageUnreachable: 'Il saggio non è raggiungibile in questo momento.',
    sageGreeting: 'Benvenuto, viaggiatore. Cosa cerca il tuo cuore?',
    suggestedQuestions: [
      'Qual è il mio cammino?',
      'Come gestire questo conflitto?',
      'Su cosa mi devo concentrare oggi?',
    ],
    aboutTitle: 'Il Libro dei Mutamenti',
    aboutP1: "Per oltre 3.000 anni, imperatori, generali e saggi si sono rivolti all'I Ching non per vedere il futuro, ma per comprendere il presente.",
    aboutP2: "È il più antico sistema binario del mondo — uno specchio che riflette le forze invisibili che plasmano la tua vita. Lanciando le monete, ti sintonizzi sul flusso antico e continuo dello Yin e dello Yang.",
    aboutQuote: '"Il Saggio non ti dice cosa fare; rivela ciò che è."',
    followUpSuggestions: ['Cosa significa la linea che cambia?', 'Dammi una pratica per oggi', 'Fai un\'altra domanda'],
    yangLabel: 'Yang ☰',
    yinLabel: 'Yin ☷',
    onboardingNamePrompt: 'Come ti chiami, cercatore?',
    onboardingAgePlaceholder: 'La tua età',
    onboardingAgePrompt: 'Quante stagioni hai vissuto?',
    onboardingNext: 'Continua →',
    welcomeBack: (name) => `Bentornato, ${name}.`,
  },
  es: {
    appTitle: 'El Oráculo del I Ching',
    appSubtitle: '¿Qué busca tu corazón?',
    inputPlaceholder: 'Pregunta al oráculo…',
    castButton: 'Lanzar las monedas',
    castHint: '(o toca las monedas para lanzar manualmente)',
    castManualProgress: (n) => `Lanzamiento manual (${n}/6)`,
    readingComplete: 'Lectura Completa',
    consultingWisdom: 'Consultando la sabiduría antigua…',
    sageUnreachable: 'El sabio no puede ser alcanzado en este momento.',
    sageGreeting: 'Bienvenido, viajero. ¿Qué busca tu corazón?',
    suggestedQuestions: [
      '¿Cuál es mi camino a seguir?',
      '¿Cómo manejar este conflicto?',
      '¿En qué debo enfocarme hoy?',
    ],
    aboutTitle: 'El Libro de los Cambios',
    aboutP1: 'Durante más de 3.000 años, emperadores, generales y sabios han recurrido al I Ching no para ver el futuro, sino para comprender el presente.',
    aboutP2: 'Es el sistema binario más antiguo del mundo — un espejo que refleja las fuerzas invisibles que dan forma a tu vida ahora mismo.',
    aboutQuote: '"El Sabio no te dice qué hacer; revela lo que es."',
    followUpSuggestions: ['¿Qué significa la línea cambiante?', 'Dame una práctica para hoy', 'Haz otra pregunta'],
    yangLabel: 'Yang ☰',
    yinLabel: 'Yin ☷',
    onboardingNamePrompt: '¿Cómo te llamas, buscador?',
    onboardingAgePlaceholder: 'Tu edad',
    onboardingAgePrompt: '¿Cuántas estaciones has vivido?',
    onboardingNext: 'Continuar →',
    welcomeBack: (name) => `Bienvenido de nuevo, ${name}.`,
  },
  fr: {
    appTitle: "L'Oracle du I Ching",
    appSubtitle: 'Que cherche ton cœur?',
    inputPlaceholder: "Interroge l'oracle…",
    castButton: 'Lancer les pièces',
    castHint: '(ou touche les pièces pour lancer manuellement)',
    castManualProgress: (n) => `Lancement manuel (${n}/6)`,
    readingComplete: 'Lecture Terminée',
    consultingWisdom: 'Consultation de la sagesse ancienne…',
    sageUnreachable: "Le sage n'est pas joignable pour l'instant.",
    sageGreeting: 'Bienvenue, voyageur. Que cherche ton cœur?',
    suggestedQuestions: [
      'Quel est mon chemin?',
      'Comment gérer ce conflit?',
      "Sur quoi dois-je me concentrer aujourd'hui?",
    ],
    aboutTitle: 'Le Livre des Mutations',
    aboutP1: "Pendant plus de 3 000 ans, empereurs, généraux et sages ont consulté le I Ching non pour voir l'avenir, mais pour comprendre le présent.",
    aboutP2: "C'est le plus ancien système binaire du monde — un miroir reflétant les forces invisibles qui façonnent votre vie en ce moment même.",
    aboutQuote: '"Le Sage ne te dit pas quoi faire ; il révèle ce qui est."',
    followUpSuggestions: ['Que signifie la ligne changeante?', 'Donne-moi une pratique pour aujourd\'hui', 'Poser une autre question'],
    yangLabel: 'Yang ☰',
    yinLabel: 'Yin ☷',
    onboardingNamePrompt: 'Quel est ton nom, chercheur?',
    onboardingAgePlaceholder: 'Ton âge',
    onboardingAgePrompt: 'Combien de saisons as-tu vécues?',
    onboardingNext: 'Continuer →',
    welcomeBack: (name) => `Bienvenue de retour, ${name}.`,
  },
  de: {
    appTitle: 'Das I Ging Orakel',
    appSubtitle: 'Was sucht dein Herz?',
    inputPlaceholder: 'Frage das Orakel…',
    castButton: 'Münzen werfen',
    castHint: '(oder tippe auf die Münzen für manuellen Wurf)',
    castManualProgress: (n) => `Manueller Wurf (${n}/6)`,
    readingComplete: 'Lesung Abgeschlossen',
    consultingWisdom: 'Konsultiere die alte Weisheit…',
    sageUnreachable: 'Der Weise ist im Moment nicht erreichbar.',
    sageGreeting: 'Willkommen, Reisender. Was sucht dein Herz?',
    suggestedQuestions: [
      'Was ist mein Weg nach vorn?',
      'Wie soll ich mit diesem Konflikt umgehen?',
      'Worauf soll ich mich heute konzentrieren?',
    ],
    aboutTitle: 'Das Buch der Wandlungen',
    aboutP1: 'Seit über 3.000 Jahren wenden sich Kaiser, Generäle und Weise dem I Ging zu — nicht um die Zukunft zu sehen, sondern um die Gegenwart zu verstehen.',
    aboutP2: 'Es ist das älteste Binärsystem der Welt — ein Spiegel, der die unsichtbaren Kräfte widerspiegelt, die dein Leben gerade jetzt formen.',
    aboutQuote: '"Der Weise sagt dir nicht, was du tun sollst; er enthüllt, was ist."',
    followUpSuggestions: ['Was bedeutet die Wandlungslinie?', 'Gib mir eine Übung für heute', 'Weitere Frage stellen'],
    yangLabel: 'Yang ☰',
    yinLabel: 'Yin ☷',
    onboardingNamePrompt: 'Wie heißt du, Suchender?',
    onboardingAgePlaceholder: 'Dein Alter',
    onboardingAgePrompt: 'Wie viele Jahreszeiten hast du erlebt?',
    onboardingNext: 'Weiter →',
    welcomeBack: (name) => `Willkommen zurück, ${name}.`,
  },
  pt: {
    appTitle: 'O Oráculo do I Ching',
    appSubtitle: 'O que busca o seu coração?',
    inputPlaceholder: 'Pergunte ao oráculo…',
    castButton: 'Lançar as moedas',
    castHint: '(ou toque nas moedas para lançar manualmente)',
    castManualProgress: (n) => `Lançamento manual (${n}/6)`,
    readingComplete: 'Leitura Completa',
    consultingWisdom: 'Consultando a sabedoria antiga…',
    sageUnreachable: 'O sábio não pôde ser alcançado neste momento.',
    sageGreeting: 'Bem-vindo, viajante. O que busca o seu coração?',
    suggestedQuestions: [
      'Qual é o meu caminho a seguir?',
      'Como lidar com este conflito?',
      'No que devo me focar hoje?',
    ],
    aboutTitle: 'O Livro das Mutações',
    aboutP1: 'Por mais de 3.000 anos, imperadores, generais e sábios recorreram ao I Ching não para ver o futuro, mas para compreender o presente.',
    aboutP2: 'É o sistema binário mais antigo do mundo — um espelho que reflete as forças invisíveis que moldam a sua vida neste exato momento.',
    aboutQuote: '"O Sábio não te diz o que fazer; revela o que é."',
    followUpSuggestions: ['O que significa a linha em mudança?', 'Dê-me uma prática para hoje', 'Fazer outra pergunta'],
    yangLabel: 'Yang ☰',
    yinLabel: 'Yin ☷',
    onboardingNamePrompt: 'Qual é o seu nome, buscador?',
    onboardingAgePlaceholder: 'A sua idade',
    onboardingAgePrompt: 'Quantas estações você viveu?',
    onboardingNext: 'Continuar →',
    welcomeBack: (name) => `Bem-vindo de volta, ${name}.`,
  },
  zh: {
    appTitle: '易经神谕',
    appSubtitle: '你的心在寻找什么？',
    inputPlaceholder: '向神谕提问……',
    castButton: '投掷铜钱',
    castHint: '（或点击铜钱手动投掷）',
    castManualProgress: (n) => `手动投掷 (${n}/6)`,
    readingComplete: '卜卦完成',
    consultingWisdom: '正在咨询古代智慧……',
    sageUnreachable: '智者此刻无法联络。',
    sageGreeting: '欢迎，旅人。你的心在寻找什么？',
    suggestedQuestions: [
      '我的道路在何方？',
      '如何处理当前的冲突？',
      '今天我应该专注于什么？',
    ],
    aboutTitle: '易经',
    aboutP1: '三千年来，帝王、将帅与圣贤求问易经，不为窥见未来，而为洞察当下。',
    aboutP2: '易经是世界上最古老的二进制系统——一面镜子，映照出此刻塑造你生命的无形力量。',
    aboutQuote: '"圣人不告诉你该做什么；他揭示的是真实。"',
    followUpSuggestions: ['变爻意味着什么？', '给我一个今日修行', '再问一个问题'],
    yangLabel: '阳 ☰',
    yinLabel: '阴 ☷',
    onboardingNamePrompt: '你叫什么名字，寻道者？',
    onboardingAgePlaceholder: '你的年龄',
    onboardingAgePrompt: '你经历了多少个季节？',
    onboardingNext: '继续 →',
    welcomeBack: (name) => `欢迎回来，${name}。`,
  },
  ja: {
    appTitle: '易経オラクル',
    appSubtitle: 'あなたの心は何を求めていますか？',
    inputPlaceholder: 'オラクルに質問する…',
    castButton: 'コインを投げる',
    castHint: '（またはコインをタップして手動で投げる）',
    castManualProgress: (n) => `手動投げ (${n}/6)`,
    readingComplete: '卦占い完了',
    consultingWisdom: '古代の知恵を参照しています…',
    sageUnreachable: '現在、賢者に連絡が取れません。',
    sageGreeting: 'ようこそ、旅人よ。あなたの心は何を求めていますか？',
    suggestedQuestions: [
      '私の進むべき道は？',
      'この葛藤にどう対処すべきか？',
      '今日集中すべきことは？',
    ],
    aboutTitle: '易経について',
    aboutP1: '3,000年以上にわたり、皇帝・将軍・賢者たちは未来を見るためではなく、現在を理解するために易経を求めてきました。',
    aboutP2: '世界最古のバイナリシステム——あなたの人生を形作る見えない力を映し出す鏡です。コインを投げることで、陰と陽の古代の流れに繋がります。',
    aboutQuote: '「賢者はあなたに何をすべきか告げない。存在するものを明かすのだ。」',
    followUpSuggestions: ['変爻の意味は？', '今日の実践を教えて', '別の質問をする'],
    yangLabel: 'Yang ☰',
    yinLabel: 'Yin ☷',
    onboardingNamePrompt: 'あなたの名前は何ですか、探求者よ？',
    onboardingAgePlaceholder: 'あなたの年齢',
    onboardingAgePrompt: '何つの季節を生きてきましたか？',
    onboardingNext: '続ける →',
    welcomeBack: (name) => `おかえりなさい、${name}。`,
  },
};

/** Detect the best locale from the browser. Falls back to 'en'. */
function detectLocale(): Locale {
  const supported = Object.keys(TRANSLATIONS) as Locale[];
  const browserLangs = navigator.languages ?? [navigator.language];
  for (const lang of browserLangs) {
    const short = lang.slice(0, 2) as Locale;
    if (supported.includes(short)) return short;
  }
  return 'en';
}

let _locale: Locale | null = null;

export function getLocale(): Locale {
  if (!_locale) _locale = detectLocale();
  return _locale;
}

export function t(): Strings {
  return TRANSLATIONS[getLocale()];
}
