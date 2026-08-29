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
      subheading: 'Un flujo de desarrollo completo asistido por IA: del diagnóstico al despliegue, con el equipo formado y los criterios de calidad bajo control.',
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
            'Gobernanza de datos, secretos y dependencias',
            'Due diligence e integración tecnológica',
          ],
        },
        {
          tag: 'SERVICIO_02',
          title: 'Análisis & Transformación IA',
          description:
            'Diagnóstico integral del proyecto —desde cero o ya en marcha— e implantación del flujo completo de desarrollo asistido por IA: entorno preparado, equipo formado y criterios de calidad bajo control.',
          features: [
            'Diagnóstico técnico y auditoría del proyecto',
            'Hoja de ruta de mejora y planificación',
            'Preparación del entorno de desarrollo asistido',
            'Implementación del flujo AI-First',
            'Formación del equipo en desarrollo asistido con IA',
            'Definición y control de criterios de calidad',
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
            'Documentación viva y contexto histórico del proyecto',
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
            'Tests automatizados como puerta de merge',
            'Revisión de código asistida por IA',
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
      subheading: 'A complete AI-assisted development workflow: from diagnosis to deployment, with the team trained and quality criteria under control.',
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
            'Data, secrets and dependency governance',
            'Due diligence & technology integration',
          ],
        },
        {
          tag: 'SERVICE_02',
          title: 'AI Analysis & Transformation',
          description:
            'Comprehensive project diagnosis — greenfield or already running — and implementation of the complete AI-assisted development workflow: environment prepared, team trained, quality criteria under control.',
          features: [
            'Technical diagnosis and project audit',
            'Improvement roadmap and planning',
            'AI-assisted development environment setup',
            'AI-First workflow implementation',
            'Team training in AI-assisted development',
            'Quality criteria definition and control',
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
            'Living documentation and project history',
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
            'Automated tests as a merge gate',
            'AI-assisted code review',
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

  contactChat: {
    es: {
      intro: 'Diagnóstico en 2 minutos. Diez preguntas y te envío un informe con mejoras concretas para vuestro flujo de trabajo.',
      progress: 'Paso {index} de {total}',
      back: '‹ Atrás',
      next: 'Continuar ›',
      skip: 'Saltar',
      sending: 'Enviando…',
      steps: {
        name: { prompt: '¿Cómo te llamas?', placeholder: 'Nombre y apellidos' },
        company: { prompt: '¿En qué empresa trabajas?', placeholder: 'Nombre de la empresa (opcional)' },
        email: { prompt: '¿A qué email te envío el informe?', placeholder: 'tu@empresa.com' },
        code: {
          prompt: 'Te he enviado un código de 6 dígitos. Escríbelo aquí.',
          placeholder: '000000',
          hint: 'Caduca en 10 minutos. Revisa la carpeta de spam si no aparece.',
          resend: 'Enviar otro código',
        },
        delivery: {
          prompt: '¿Cómo usáis la IA en el desarrollo hoy?',
          options: {
            noAi: 'Todavía no la usamos',
            aiAssistedEditor: 'Autocompletado en el editor',
            aiAgents: 'Agentes integrados en el flujo',
            unsure: 'No lo tengo claro',
          },
        },
        bugs: {
          prompt: '¿Cómo gestionáis los bugs?',
          options: {
            manualTriage: 'Triaje manual, sin herramienta',
            trackerOnly: 'Gestor de incidencias, sin automatizar',
            testsGate: 'Tests automáticos que bloquean el merge',
            aiTriage: 'Triaje y diagnóstico asistidos por IA',
          },
        },
        deploys: {
          prompt: '¿Cómo desplegáis a producción?',
          options: {
            manual: 'A mano, cuando toca',
            scripted: 'Con scripts propios',
            pipeline: 'Pipeline de CI/CD',
            continuous: 'Entrega continua, varias veces al día',
          },
        },
        security: {
          prompt: '¿Y la seguridad y las dependencias?',
          options: {
            none: 'Sin proceso definido',
            manualReviews: 'Revisiones manuales',
            dependencyScanning: 'Escaneo de dependencias (Snyk o similar)',
            scanningAndPolicies: 'Escaneo más políticas y bloqueo automático',
          },
        },
        observability: {
          prompt: '¿Cómo detectáis que algo se ha roto en producción?',
          options: {
            none: 'Cuando nos avisa un cliente',
            logsOnly: 'Revisando logs a mano',
            errorMonitoring: 'Monitorización de errores con alertas',
            fullObservability: 'Observabilidad completa: métricas, trazas y alertas',
          },
        },
        website: {
          prompt: '¿Cuál es vuestra web o aplicación?',
          placeholder: 'empresa.com (opcional)',
          hint: 'Miro solo la portada, para incluir datos objetivos en el informe.',
        },
        consent: {
          prompt: 'Para generar y enviarte el informe necesito tu consentimiento.',
          label: 'Acepto que se analice la web indicada y se me envíe el informe por email. He leído la',
          privacyLinkLabel: 'Política de privacidad',
        },
      },
      success: {
        title: 'Informe en camino',
        body: 'Te lo he enviado a tu email. Si algo no cuadra, responde a ese mensaje y lo revisamos.',
      },
      errors: {
        required: 'Este campo es obligatorio.',
        invalidEmail: 'Ese email no parece válido.',
        invalidCode: 'El código son 6 dígitos.',
        invalidChoice: 'Elige una de las opciones.',
        invalidUrl: 'Escribe un dominio válido, por ejemplo empresa.com.',
        consentRequired: 'Necesito tu consentimiento para continuar.',
        tooLong: 'El texto es demasiado largo.',
        humanCheck: 'No he podido verificar que eres una persona. Recarga la página e inténtalo de nuevo.',
        codeRejected: 'Ese código no es válido. Pide uno nuevo.',
        unavailable: 'El servicio no está disponible ahora mismo. Inténtalo en unos minutos.',
        network: 'No he podido conectar con el servidor. Comprueba tu conexión.',
        expired: 'La verificación ha caducado. Vuelve a pedir un código.',
        generic: 'Algo ha fallado. Inténtalo de nuevo.',
      },
    },
    en: {
      intro: 'A two-minute diagnosis. Ten questions and I will email you a report with concrete improvements for your workflow.',
      progress: 'Step {index} of {total}',
      back: '‹ Back',
      next: 'Continue ›',
      skip: 'Skip',
      sending: 'Sending…',
      steps: {
        name: { prompt: "What's your name?", placeholder: 'Full name' },
        company: { prompt: 'Which company do you work for?', placeholder: 'Company name (optional)' },
        email: { prompt: 'Where should I send the report?', placeholder: 'you@company.com' },
        code: {
          prompt: "I've sent you a 6-digit code. Type it here.",
          placeholder: '000000',
          hint: 'It expires in 10 minutes. Check your spam folder if it does not arrive.',
          resend: 'Send another code',
        },
        delivery: {
          prompt: 'How do you use AI in development today?',
          options: {
            noAi: 'We do not use it yet',
            aiAssistedEditor: 'Autocomplete in the editor',
            aiAgents: 'Agents wired into the workflow',
            unsure: 'Not sure',
          },
        },
        bugs: {
          prompt: 'How do you handle bugs?',
          options: {
            manualTriage: 'Manual triage, no tooling',
            trackerOnly: 'Issue tracker, nothing automated',
            testsGate: 'Automated tests gating the merge',
            aiTriage: 'AI-assisted triage and diagnosis',
          },
        },
        deploys: {
          prompt: 'How do you deploy to production?',
          options: {
            manual: 'By hand, when needed',
            scripted: 'With our own scripts',
            pipeline: 'A CI/CD pipeline',
            continuous: 'Continuous delivery, several times a day',
          },
        },
        security: {
          prompt: 'What about security and dependencies?',
          options: {
            none: 'No defined process',
            manualReviews: 'Manual reviews',
            dependencyScanning: 'Dependency scanning (Snyk or similar)',
            scanningAndPolicies: 'Scanning plus policies and automatic blocking',
          },
        },
        observability: {
          prompt: 'How do you find out something broke in production?',
          options: {
            none: 'When a customer tells us',
            logsOnly: 'By reading logs by hand',
            errorMonitoring: 'Error monitoring with alerts',
            fullObservability: 'Full observability: metrics, traces and alerts',
          },
        },
        website: {
          prompt: 'What is your website or app?',
          placeholder: 'company.com (optional)',
          hint: 'I only look at the home page, to put objective data in the report.',
        },
        consent: {
          prompt: 'To generate and send the report I need your consent.',
          label: 'I agree to the analysis of the site above and to receiving the report by email. I have read the',
          privacyLinkLabel: 'Privacy Policy',
        },
      },
      success: {
        title: 'Report on its way',
        body: 'I have sent it to your inbox. If anything looks off, reply to that email and we will go through it.',
      },
      errors: {
        required: 'This field is required.',
        invalidEmail: 'That email does not look valid.',
        invalidCode: 'The code is 6 digits.',
        invalidChoice: 'Pick one of the options.',
        invalidUrl: 'Enter a valid domain, for example company.com.',
        consentRequired: 'I need your consent to continue.',
        tooLong: 'That text is too long.',
        humanCheck: 'I could not verify you are a person. Reload the page and try again.',
        codeRejected: 'That code is not valid. Request a new one.',
        unavailable: 'The service is unavailable right now. Try again in a few minutes.',
        network: 'I could not reach the server. Check your connection.',
        expired: 'Verification expired. Request a new code.',
        generic: 'Something went wrong. Try again.',
      },
    },
  },
  contactConversation: {
    es: {
      // Openings rotate per conversation. Every one of them must say the same
      // three things — who is asking, that there will be questions, and that the
      // point is the report — because a greeting that omits the purpose turns the
      // questions that follow into an interrogation.
      openings: [
        'Hola, soy el asistente de CODE29. Te haré unas pocas preguntas sobre cómo trabajáis y con eso te preparo un informe con la hoja de ruta de vuestro flujo de desarrollo. ¿Cómo te llamas?',
        'Buenas. Antes de nada: esto es una conversación corta, no un formulario. Con lo que me cuentes te preparo un informe a medida sobre vuestro flujo de desarrollo. Empecemos por lo fácil, ¿cómo te llamas?',
        'Soy el asistente de CODE29. Mi trabajo aquí es entender cómo desarrolláis para escribirte un informe con lo que mejoraría. Serán cuatro o cinco preguntas. ¿Con quién hablo?',
        'Hola. Voy a hacerte unas preguntas sobre vuestro día a día de desarrollo y a cambio te mando un informe con la hoja de ruta que sacaría de ellas. ¿Cómo te llamas?',
        'Hola, soy el asistente de CODE29. Cuanto mejor entienda cómo trabajáis, más útil será el informe que te envíe al final. Empecemos: ¿cómo te llamas?',
      ],
      placeholder: 'Escribe tu respuesta…',
      typing: 'CODE29 está escribiendo…',
      send: 'Enviar',
      sending: 'Enviando…',
      you: 'Tú',
      assistant: 'CODE29',
      threadLabel: 'Conversación',
      verify: {
        // The request for the address is NOT here: the model writes it,
        // because the server tells it that this is the step. A canned
        // sentence beside the model's own question is how one turn came to
        // carry two.
        //
        // What remains is the confirmation that a code went out — the server
        // never learns that happened, so nobody else can say it.
        askCode: [
          'Te acabo de enviar un código. Escríbelo aquí y seguimos.',
          'Ya va el código camino de tu bandeja. Pégalo aquí y continuamos.',
          'Mira tu correo: te he mandado un código. En cuanto lo escribas, seguimos.',
        ],
        // Said by the bot, in the thread. There is no field to raise an alert
        // under any more, and that is deliberate: a form warns, a conversation
        // tells you and keeps going.
        codeRejected: [
          'Ese código no me cuadra. ¿Lo miras otra vez?',
          'No me sale ese código. Revísalo y me lo dices.',
          'Ese no es. Échale un ojo al correo y prueba otra vez.',
        ],
        humanCheck: [
          'No he podido confirmar que eres una persona. Recarga la página y seguimos.',
          'Se me ha atascado la comprobación anti-robots. Prueba a recargar y me lo cuentas otra vez.',
        ],
        verified: [
          'Perfecto, email verificado.',
          'Listo, ya sé dónde encontrarte.',
          'Verificado. Seguimos.',
        ],
      },
      done: {
        title: 'Informe en camino',
        body: 'Te lo envío al email verificado. Si algo no cuadra, responde a ese mensaje.',
      },
      exhausted: [
        'Con esto tengo suficiente para preparar tu informe.',
        'Ya tengo material de sobra. Me pongo con el informe.',
        'Creo que tengo lo que necesito. Paso a escribirlo.',
      ],
      // No detail, on purpose: someone who learns which phrasing ended the
      // conversation learns how to word the next attempt.
      blocked: {
        title: 'Conversación terminada',
        body: 'No puedo continuar con esta conversación. Si crees que es un error, escríbenos a hola@code29.dev.',
      },
      errors: {
        empty: 'Escribe algo antes de enviar.',
        tooLong: 'El mensaje es demasiado largo. Resúmelo un poco.',
        expired: 'La conversación ha caducado. Escribe de nuevo para empezar otra.',
        retry: 'No he podido procesar tu mensaje. Inténtalo otra vez.',
        unavailable: 'El servicio no está disponible ahora mismo. Inténtalo en unos minutos.',
        network: 'No he podido conectar con el servidor. Comprueba tu conexión.',
        invalidEmail: 'Ese email no parece válido.',
        codeRejected: 'Ese código no es válido. Pide uno nuevo.',
        humanCheck:
          'No he podido verificar que eres una persona. Recarga la página e inténtalo de nuevo.',
        generic: 'Algo ha fallado. Inténtalo de nuevo.',
      },
    },
    en: {
      openings: [
        'Hi, I am the CODE29 assistant. I will ask you a few questions about how your team works, and from those I will put together a report with a roadmap for your development workflow. What is your name?',
        'Hello. First things first: this is a short conversation, not a form. From what you tell me I will write you a report tailored to your development workflow. Let us start easy — what is your name?',
        'I am the CODE29 assistant. My job here is to understand how you build, so I can write you a report on what I would improve. Four or five questions. Who am I speaking with?',
        'Hi. I am going to ask about your day-to-day development, and in return I will send you a report with the roadmap I draw from it. What is your name?',
        'Hi, I am the CODE29 assistant. The better I understand how you work, the more useful the report I send you at the end. Let us begin: what is your name?',
      ],
      placeholder: 'Type your answer…',
      typing: 'CODE29 is typing…',
      send: 'Send',
      sending: 'Sending…',
      you: 'You',
      assistant: 'CODE29',
      threadLabel: 'Conversation',
      verify: {
        // The request for the address is NOT here: the model writes it,
        // because the server tells it that this is the step. A canned
        // sentence beside the model's own question is how one turn came to
        // carry two.
        //
        // What remains is the confirmation that a code went out — the server
        // never learns that happened, so nobody else can say it.
        askCode: [
          'I have just sent you a code. Type it here and we carry on.',
          'The code is on its way to your inbox. Paste it here and we continue.',
          'Check your email: I sent you a code. Type it and we keep going.',
        ],
        codeRejected: [
          'That code does not match. Care to check it again?',
          'I am not getting that code. Have another look and tell me.',
          'That is not the one. Check the email and try again.',
        ],
        humanCheck: [
          'I could not confirm you are a person. Reload the page and we carry on.',
          'The anti-robot check got stuck. Try reloading and tell me again.',
        ],
        verified: [
          'Great, your email is verified.',
          'Done — now I know where to find you.',
          'Verified. Let us carry on.',
        ],
      },
      done: {
        title: 'Report on its way',
        body: 'I am sending it to the verified address. If anything looks off, reply to that email.',
      },
      exhausted: [
        'That is enough for me to prepare your report.',
        'I have plenty to work with. Let me write it up.',
        'I think I have what I need. On to the report.',
      ],
      blocked: {
        title: 'Conversation ended',
        body: 'I cannot continue this conversation. If you think that is a mistake, write to us at hola@code29.dev.',
      },
      errors: {
        empty: 'Write something before sending.',
        tooLong: 'That message is too long. Trim it a little.',
        expired: 'The conversation expired. Write again to start a new one.',
        retry: 'I could not process your message. Try again.',
        unavailable: 'The service is unavailable right now. Try again in a few minutes.',
        network: 'I could not reach the server. Check your connection.',
        invalidEmail: 'That email does not look valid.',
        codeRejected: 'That code is not valid. Request a new one.',
        humanCheck: 'I could not verify you are a person. Reload the page and try again.',
        generic: 'Something went wrong. Try again.',
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
