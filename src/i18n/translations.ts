// Master translations file — all UI copy for ES and EN
// Pure ESM module: importable in Astro (server) and client-side scripts

export const translations = {
  nav: {
    es: {
      links: [
        { label: 'Servicios', href: '#services' },
        { label: 'Stack', href: '#stack' },
        { label: 'Testimonios', href: '#testimonials' },
      ],
      cta: 'Iniciar proyecto',
    },
    en: {
      links: [
        { label: 'Services', href: '#services' },
        { label: 'Stack', href: '#stack' },
        { label: 'Testimonials', href: '#testimonials' },
      ],
      cta: 'Start project',
    },
  },

  hero: {
    es: {
      tag: 'THE NEON ARCHITECT',
      headlinePart1: 'Arquitectando el futuro de la',
      headlineAccent: 'inteligencia empresarial',
      subheadline:
        'Uniendo la intuición humana con la inteligencia artificial.\nCTO as a Service & AI Developer — Miguel Navarro Mantas',
      ctaPrimary: 'INICIALIZAR_PROTOCOLO ›',
      ctaSecondary: 'VER_SERVICIOS',
      status: 'ESTADO_DEL_SISTEMA: OPTIMIZADO | MATRIZ_IA: 99.8% | CIFRADO: AES-256',
    },
    en: {
      tag: 'THE NEON ARCHITECT',
      headlinePart1: 'Architecting the future of',
      headlineAccent: 'enterprise intelligence',
      subheadline:
        'Bridging human intuition with artificial intelligence.\nCTO as a Service & AI Developer — Miguel Navarro Mantas',
      ctaPrimary: 'INITIALIZE_PROTOCOL ›',
      ctaSecondary: 'VIEW_SERVICES',
      status: 'SYSTEM_STATUS: OPTIMIZED | AI_MATRIX: 99.8% | ENCRYPTION: AES-256',
    },
  },

  stats: {
    es: [
      {
        value: '2x–3x',
        label: 'Velocidad de desarrollo',
        detail: 'Aceleración vía orquestación de agentes IA en el SDLC',
      },
      {
        value: '-60%',
        label: 'Errores en producción',
        detail: 'Auditorías automatizadas continuas sobre el código',
      },
      {
        value: 'M+',
        label: 'Transacciones diarias',
        detail: 'Arquitecturas probadas a escala empresarial',
      },
      {
        value: 'Zero',
        label: 'Trust Architecture',
        detail: 'Seguridad AES-256 integrada en todas las capas del sistema',
      },
    ],
    en: [
      {
        value: '2x–3x',
        label: 'Development speed',
        detail: 'Acceleration via AI agent orchestration in the SDLC',
      },
      {
        value: '-60%',
        label: 'Production errors',
        detail: 'Continuous automated code audits',
      },
      {
        value: 'M+',
        label: 'Daily transactions',
        detail: 'Battle-tested architectures at enterprise scale',
      },
      {
        value: 'Zero',
        label: 'Trust Architecture',
        detail: 'AES-256 security integrated at every layer of the system',
      },
    ],
  },

  educationStack: {
    es: {
      sectionTagEducation: 'FORMATION_DATA',
      heading: 'Máster en Desarrollo con IA',
      description:
        'Especialización en optimización del desarrollo con inteligencia artificial. Investigación principal: Orquestación de agentes autónomos y sistemas de inteligencia distribuida.',
      experienceSummary:
        'Más de 10 años trabajando con APIs, gestión de eCommerce y software de retail desplegado en mercados de todo el mundo. Experiencia conectando operativa, producto y tecnología en entornos de alta exigencia.',
      metaSpecialization: 'Especialización',
      metaSpecializationValue: 'Inteligencia Artificial',
      metaMethodology: 'Metodología',
      metaMethodologyValue: 'SDLC AI-First',
      metaExperience: 'Experiencia',
      metaExperienceValue: '15+ proyectos',
      sectionTagStack: 'CORE_STACK',
      stackAriaLabel: 'Tecnologías',
      // Stack item names: kept identical in both langs (proper nouns / product names)
      items: [
        { name: 'Python', category: 'backend' },
        { name: 'FastAPI', category: 'backend' },
        { name: 'LangChain', category: 'ai' },
        { name: 'LangGraph', category: 'ai' },
        { name: 'OpenAI API', category: 'ai' },
        { name: 'Vector DBs', category: 'ai' },
        { name: 'Astro', category: 'frontend' },
        { name: 'Vue 3', category: 'frontend' },
        { name: 'TypeScript', category: 'frontend' },
        { name: 'Node.js', category: 'backend' },
        { name: 'PostgreSQL', category: 'backend' },
        { name: 'Docker', category: 'infra' },
        { name: 'Vercel', category: 'infra' },
        { name: 'GitHub Actions', category: 'infra' },
        { name: 'Kubernetes', category: 'infra' },
      ],
    },
    en: {
      sectionTagEducation: 'FORMATION_DATA',
      heading: 'AI Development Master\'s Degree',
      description:
        'Specialization in optimizing development with artificial intelligence. Main research: Autonomous agent orchestration and distributed intelligence systems.',
      experienceSummary:
        'More than 10 years working with APIs, eCommerce operations, and retail software deployed across global markets. Experience connecting operations, product, and technology in high-demand environments.',
      metaSpecialization: 'Specialization',
      metaSpecializationValue: 'Artificial Intelligence',
      metaMethodology: 'Methodology',
      metaMethodologyValue: 'AI-First SDLC',
      metaExperience: 'Experience',
      metaExperienceValue: '15+ projects',
      sectionTagStack: 'CORE_STACK',
      stackAriaLabel: 'Technologies',
      // Stack item names: identical to ES (proper nouns / product names)
      items: [
        { name: 'Python', category: 'backend' },
        { name: 'FastAPI', category: 'backend' },
        { name: 'LangChain', category: 'ai' },
        { name: 'LangGraph', category: 'ai' },
        { name: 'OpenAI API', category: 'ai' },
        { name: 'Vector DBs', category: 'ai' },
        { name: 'Astro', category: 'frontend' },
        { name: 'Vue 3', category: 'frontend' },
        { name: 'TypeScript', category: 'frontend' },
        { name: 'Node.js', category: 'backend' },
        { name: 'PostgreSQL', category: 'backend' },
        { name: 'Docker', category: 'infra' },
        { name: 'Vercel', category: 'infra' },
        { name: 'GitHub Actions', category: 'infra' },
        { name: 'Kubernetes', category: 'infra' },
      ],
    },
  },

  services: {
    es: {
      sectionTag: 'WHAT_I_DO',
      heading: 'Servicios',
      subheading: 'Soluciones diseñadas para empresas que quieren moverse más rápido con la inteligencia correcta.',
      cta: 'Solicitar información ›',
      items: [
        {
          tag: 'SERVICIO_01',
          title: 'CTO as a Service',
          description:
            'Dirección técnica estratégica, definición de arquitectura y escalado del equipo. Liderazgo ejecutivo sin la estructura de un CTO a tiempo completo.',
          features: [
            'Arquitectura de sistemas escalables',
            'Gestión y crecimiento del equipo técnico',
            'Definición de roadmap tecnológico',
            'Due diligence e integración tecnológica',
          ],
        },
        {
          tag: 'SERVICIO_02',
          title: 'Análisis & Transformación IA',
          description:
            'Diagnóstico integral del proyecto —desde cero o ya en marcha— diseño del plan de mejora e implantación del flujo de desarrollo asistido por IA, incluyendo la capacitación del equipo.',
          features: [
            'Diagnóstico técnico y auditoría del proyecto',
            'Hoja de ruta de mejora y planificación',
            'Implementación del flujo AI-First',
            'Capacitación del equipo en desarrollo asistido con IA',
          ],
        },
        {
          tag: 'SERVICIO_03',
          title: 'AI Project Manager',
          description:
            'Integración de IA en productos existentes, automatización de procesos y aceleración del time-to-market mediante flujos de trabajo aumentados por inteligencia artificial.',
          features: [
            'Integración avanzada de LLMs',
            'Orquestación de agentes autónomos',
            'Automatización de flujos de desarrollo',
            'Hoja de ruta estratégica de IA',
          ],
        },
        {
          tag: 'SERVICIO_04',
          title: 'Automatización de despliegue DevOps con IA',
          description:
            'Diseño e implantación de pipelines inteligentes de CI/CD, observabilidad y automatización operativa para desplegar más rápido, con menos fricción y más control.',
          features: [
            'Pipelines CI/CD asistidos por IA',
            'Automatización de despliegues y rollback',
            'Observabilidad y alertado operativo',
            'Optimización de entornos y costes de infraestructura',
          ],
        },
      ],
    },
    en: {
      sectionTag: 'WHAT_I_DO',
      heading: 'Services',
      subheading: 'Solutions built for companies that want to move faster with the right intelligence.',
      cta: 'Request information ›',
      items: [
        {
          tag: 'SERVICE_01',
          title: 'CTO as a Service',
          description:
            'Strategic technical leadership, architecture definition, and team scaling. Executive direction without the overhead of a full-time CTO.',
          features: [
            'Scalable systems architecture',
            'Technical team management & growth',
            'Technology roadmap definition',
            'Due diligence & technology integration',
          ],
        },
        {
          tag: 'SERVICE_02',
          title: 'AI Analysis & Transformation',
          description:
            'Comprehensive project diagnosis — from scratch or already in progress — design of the improvement plan and implementation of the AI-assisted development workflow, including team training.',
          features: [
            'Technical diagnosis and project audit',
            'Improvement roadmap and planning',
            'AI-First workflow implementation',
            'Team training in AI-assisted development',
          ],
        },
        {
          tag: 'SERVICE_03',
          title: 'AI Project Manager',
          description:
            'AI integration into existing products, process automation, and time-to-market acceleration through AI-augmented development workflows.',
          features: [
            'Advanced LLM integration',
            'Autonomous agent orchestration',
            'Development workflow automation',
            'Strategic AI roadmap',
          ],
        },
        {
          tag: 'SERVICE_04',
          title: 'AI-Powered DevOps Deployment Automation',
          description:
            'Design and implementation of intelligent CI/CD pipelines, observability, and operational automation so you can deploy faster with less friction and more control.',
          features: [
            'AI-assisted CI/CD pipelines',
            'Deployment and rollback automation',
            'Observability and operational alerting',
            'Infrastructure environment and cost optimization',
          ],
        },
      ],
    },
  },

  toolbelt: {
    es: {
      title: 'ACTIVE_TOOLCHAIN',
      ariaLabel: 'Herramientas y plataformas con las que trabajo',
      items: [
        { label: 'GitHub', icon: 'github' },
        { label: 'Jira', icon: 'jira' },
        { label: 'AWS', icon: 'aws' },
        { label: 'Linear', icon: 'linear' },
        { label: 'VS Code', icon: 'vscode' },
        { label: 'Android', icon: 'android' },
        { label: 'VPN', icon: 'vpn' },
        { label: 'AI', icon: 'ai' },
        { label: 'Copilot', icon: 'copilot' },
        { label: 'Claude', icon: 'claude' },
        { label: 'Gemini', icon: 'gemini' },
        { label: 'Codex', icon: 'codex' },
        { label: 'Docker', icon: 'docker' },
      ],
    },
    en: {
      title: 'ACTIVE_TOOLCHAIN',
      ariaLabel: 'Tools and platforms I work with',
      items: [
        { label: 'GitHub', icon: 'github' },
        { label: 'Jira', icon: 'jira' },
        { label: 'AWS', icon: 'aws' },
        { label: 'Linear', icon: 'linear' },
        { label: 'VS Code', icon: 'vscode' },
        { label: 'Android', icon: 'android' },
        { label: 'VPN', icon: 'vpn' },
        { label: 'AI', icon: 'ai' },
        { label: 'Copilot', icon: 'copilot' },
        { label: 'Claude', icon: 'claude' },
        { label: 'Gemini', icon: 'gemini' },
        { label: 'Codex', icon: 'codex' },
        { label: 'Docker', icon: 'docker' },
      ],
    },
  },

  testimonials: {
    es: {
      sectionTag: 'SOCIAL_PROOF',
      heading: 'Lo que dicen mis clientes',
      items: [
        {
          quote:
            'La integración de IA en nuestro flujo de trabajo duplicó la velocidad de entrega en tres meses. Miguel entiende el negocio y el código en igual medida.',
          name: 'Javier Domínguez',
          role: 'CEO',
          company: 'TechFlow Solutions',
        },
        {
          quote:
            'Diseñó una infraestructura impecable para nuestro entorno crítico, reduciendo los errores en producción un 50%. Exactamente lo que necesitábamos.',
          name: 'Elena Martí',
          role: 'Product Director',
          company: 'IBEX Corp',
        },
        {
          quote:
            'Sus capacidades como AI Project Manager son excepcionales. Transformó la cultura de nuestro equipo hacia una eficiencia real y medible.',
          name: 'Ricardo Costa',
          role: 'CTO',
          company: 'Global E-commerce',
        },
      ],
    },
    en: {
      sectionTag: 'SOCIAL_PROOF',
      heading: 'What my clients say',
      items: [
        {
          quote:
            'Integrating AI into our workflow doubled our delivery speed in three months. Miguel understands business and code in equal measure.',
          name: 'Javier Domínguez',
          role: 'CEO',
          company: 'TechFlow Solutions',
        },
        {
          quote:
            'He designed flawless infrastructure for our critical environment, reducing production errors by 50%. Exactly what we needed.',
          name: 'Elena Martí',
          role: 'Product Director',
          company: 'IBEX Corp',
        },
        {
          quote:
            'His capabilities as an AI Project Manager are exceptional. He transformed our team culture toward real, measurable efficiency.',
          name: 'Ricardo Costa',
          role: 'CTO',
          company: 'Global E-commerce',
        },
      ],
    },
  },

  contact: {
    es: {
      tag: 'ENLACE_DIRECTO',
      title: 'Iniciemos la conexión',
      subtitle:
        'Sistema en línea. Listo para recibir tu propuesta de proyecto. Tiempo de respuesta estimado: < 24h.',
      status: 'STATUS: SISTEMA_ONLINE | CIFRADO: EXTREMO_A_EXTREMO | LATENCIA: <12MS',
      form: {
        fullNameLabel: 'Nombre completo',
        fullNamePlaceholder: 'Tu nombre',
        companyLabel: 'Empresa / organización',
        companyPlaceholder: 'Nombre de la empresa',
        emailLabel: 'Email',
        emailPlaceholder: 'nombre@empresa.com',
        messageLabel: 'Mensaje',
        messagePlaceholder: 'Describe tu proyecto, reto técnico o necesidad de negocio.',
        submitIdle: 'ENVIAR_MENSAJE ›',
        submitLoading: 'TRANSMITIENDO...',
        successTitle: 'Canal abierto.',
        successMessage: 'Tu mensaje ha sido enviado correctamente. Te responderé lo antes posible.',
        errorTitle: 'Transmisión interrumpida.',
        errorFallback:
          'No he podido enviar tu mensaje ahora mismo. Inténtalo de nuevo en unos minutos.',
        validationSummary: 'Revisa los campos marcados antes de enviar el mensaje.',
        privacyPrefix: 'Al enviar este formulario aceptas la',
        privacyLinkLabel: 'Política de Privacidad',
        validation: {
          required: 'Este campo es obligatorio.',
          invalidEmail: 'Introduce un email válido.',
          tooLong: 'El contenido supera la longitud permitida.',
          spam: 'Se ha detectado un envío no válido.',
        },
      },
    },
    en: {
      tag: 'DIRECT_LINK',
      title: 'Let us open the channel',
      subtitle:
        'System online. Ready to receive your project proposal. Estimated response time: < 24h.',
      status: 'STATUS: SYSTEM_ONLINE | ENCRYPTION: END_TO_END | LATENCY: <12MS',
      form: {
        fullNameLabel: 'Full name',
        fullNamePlaceholder: 'Your name',
        companyLabel: 'Company / organization',
        companyPlaceholder: 'Company name',
        emailLabel: 'Email',
        emailPlaceholder: 'name@company.com',
        messageLabel: 'Message',
        messagePlaceholder: 'Describe your project, technical challenge, or business need.',
        submitIdle: 'SEND_MESSAGE ›',
        submitLoading: 'TRANSMITTING...',
        successTitle: 'Channel open.',
        successMessage: 'Your message has been sent successfully. I will get back to you soon.',
        errorTitle: 'Transmission interrupted.',
        errorFallback:
          'I could not send your message right now. Please try again in a few minutes.',
        validationSummary: 'Review the highlighted fields before sending the message.',
        privacyPrefix: 'By sending this form you accept the',
        privacyLinkLabel: 'Privacy Policy',
        validation: {
          required: 'This field is required.',
          invalidEmail: 'Enter a valid email address.',
          tooLong: 'The content exceeds the allowed length.',
          spam: 'An invalid submission was detected.',
        },
      },
    },
  },

  footer: {
    es: {
      status: 'STATUS: SISTEMA_ONLINE | UPTIME: 99.99% | CIFRADO: AES-256',
      copy: '© 2026 CODE29 // TODOS LOS DERECHOS RESERVADOS',
      legalLinks: [
        { label: 'Aviso Legal', href: '/legal-notice' },
        { label: 'Privacidad', href: '/privacy-policy' },
        { label: 'Cookies', href: '/cookies' },
      ],
      cookiePreferences: 'Preferencias de cookies',
    },
    en: {
      status: 'STATUS: SYSTEM_ONLINE | UPTIME: 99.99% | ENCRYPTION: AES-256',
      copy: '© 2026 CODE29 // ALL RIGHTS RESERVED',
      legalLinks: [
        { label: 'Legal Notice', href: '/legal-notice' },
        { label: 'Privacy', href: '/privacy-policy' },
        { label: 'Cookies', href: '/cookies' },
      ],
      cookiePreferences: 'Cookie preferences',
    },
  },
} as const

export type Lang = 'es' | 'en'
export type Translations = typeof translations
