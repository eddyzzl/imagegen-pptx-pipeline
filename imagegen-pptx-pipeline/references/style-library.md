# Built-In PPT Style Library

Use this library when generating ImageGen style directions. A style is a visual system, not a content strategy. Style options may change art direction, typography, material, image treatment, diagram rendering, density, and pacing, but they must preserve the locked slide order, claims, data, proof objects, and selected narrative treatment.

Every style lane should record:

- `style_id`: one canonical id from this file, or `custom-*` when the user supplied a style outside the library.
- `style_source`: `built-in-style-library`, `user-specified`, or `custom-derived-from-reference`.
- `style_name`: a reader-friendly name.
- `aesthetic_family`: the broader family, such as consulting-report, annual-report, keynote-launch, workspace-minimal, editorial-gallery, academic, or industry-specific.
- `visual_signature`: concrete visual rules that distinguish the style at thumbnail scale.

Do not use a firm, product, or publication logo unless the user supplied verified brand assets. Names such as McKinsey, Apple, Notion, JPMorgan, Morgan Stanley, Bain, BCG, Deloitte, IBM, Intel, BASF, Spotify, or university references mean "inspired by common presentation conventions", not official affiliation.

## Selection Heuristics

- First classify the deck task, audience, and occasion. Candidate styles must be justified by that profile before they are shown to the user.
- Company or enterprise introduction decks: start with corporate-profile, brand-proposal, editorial-gallery, or justified annual-report treatments. Do not offer promotion, interview, or academic defense styles unless the user asks for a personal/academic framing.
- Product launch or product introduction decks: start with keynote-launch, product-launch, product-technical, product-surface, spatial-3d, or workspace-minimal styles.
- Technical, AI, model, SaaS, industry, and operations decks: start with technical-schematic, data-visual, enterprise-saas, industry-system, logistics-system, or healthcare styles.
- Strategy, consulting, research, board, and executive decision decks: start with consulting-report, research-report, boardroom, annual-report, or financial-report styles.
- Finance, investor, earnings, fundraising, and roadshow decks: start with annual-report, financial-report, investor-finance, or fintech/industry-finance styles.
- Sales, GTM, proposal, and solution decks: start with brand-proposal, product-technical, product-launch, company-profile, or evidence-led research/report styles.
- Training, onboarding, course, and enablement decks: start with training, lecture, workspace-minimal, or education styles.
- Defense, promotion, interview, personal performance, and thesis decks: start with promotion-defense, personal-performance, interview-case, rigorous-academic, thesis-defense, or conference styles. Do not start with company-profile, annual-report, or system-dashboard styles unless the user explicitly asks for that framing.
- Portfolio, creative, culture, lifestyle, and event decks: start with editorial-gallery, magazine, vintage, natural, ceremony, travel, or luxury-event styles.

For multiple style options, vary the visual system and layout archetype at thumbnail scale. Options that keep the same central loop, four-card ring, metric strip, or equal-card grid while only changing icons, lines, labels, or accent colors are not valid separate styles.

## Canonical Styles

### Consulting And Research

| style_id | style_name | aesthetic_family | Best for | Visual signature | Avoid |
|---|---|---|---|---|---|
| `mckinsey-consulting-report` | McKinsey-style consulting report | consulting-report | strategy, diagnosis, board memo | white field, strict grid, sharp section headers, issue trees, waterfall/bridge charts, sparse accent color | fake logos, decorative depth, vague cards |
| `bain-red-dot-consulting` | Bain-like red-dot consulting | consulting-report | market research, M&A, performance review | warm white, red accents, crisp chart modules, executive headlines, clean tabular evidence | turning red into a one-note theme |
| `bcg-green-impact-report` | BCG-like green impact report | consulting-report | sustainability, retail, transformation | green/black accent, circular ecosystem charts, understated photography, nature-data pairing | stock ESG decoration |
| `deloitte-insight-minimal` | Deloitte-style insight report | consulting-report | trends, human capital, future of work | black/white editorial blocks, green accents, strong report titles, evidence panels | playful colors that weaken authority |
| `ibm-dynamic-finance` | IBM-like dynamic finance | consulting-report | finance, cloud, enterprise AI | geometric green/blue data blocks, diagrammatic arrows, dark accents, technical clarity | dashboard labels as style names |
| `whitepaper-curve-pattern` | Whitepaper curve pattern | research-report | tech trends, policy, research | white background, fine mesh or wave motif, one strong curve, minimal copy | fake technical texture |
| `black-white-strategy` | Black-white strategy studio | research-report | strategy, trend, culture | stark black/white contrast, oversized type, documentary imagery, rigid grid | unreadable reversed microtext |
| `youthful-trend-report` | Youthful trend report | research-report | culture, consumer, Gen Z | bold type, sticker-like modules, bright accents, collage blocks | childish visuals for formal audiences |
| `playful-futures-report` | Playful futures report | research-report | creative trends, community, culture | colorful illustration panels, bold labels, optimistic composition | mascot overload |
| `premium-market-survey` | Premium market survey | research-report | industry survey, tariff, market scan | deep blue overlay photography, strong title block, source strip, structured findings | generic blue tech gradients |

### Finance, Investor, And Annual Report

| style_id | style_name | aesthetic_family | Best for | Visual signature | Avoid |
|---|---|---|---|---|---|
| `enterprise-annual-report` | Enterprise annual report | annual-report | annual review, company profile, CSR | premium print rules, generous margins, restrained charts, polished photography | unsupported numbers |
| `shareholder-letter-editorial` | Shareholder letter editorial | annual-report | CEO letter, board update | serif typography, architectural photo, human-scale narrative blocks | magazine prettiness without evidence |
| `jpmorgan-financial-supplement` | JPMorgan-like financial supplement | financial-report | earnings supplement, quarterly report | gray/white architecture, conservative typography, subtle blue lines, table discipline | fake official branding |
| `morgan-stanley-earnings` | Morgan Stanley-like earnings | financial-report | fixed income, investor update | white/blue city imagery, clear title hierarchy, restrained chart panels | overloaded charts |
| `quarterly-10q-clean` | Clean 10-Q report | financial-report | quarterly filing summary | plain white, strong report title, blue footer strip, evidence-first tables | decorative icons |
| `proxy-statement-modern` | Modern proxy statement | financial-report | governance, board, annual meeting | white and architectural blue, calm typography, governance modules | casual illustration |
| `portfolio-thesis-premium` | Portfolio thesis premium | investor-finance | fund thesis, portfolio review | circular thesis object, neutral paper, gold/black accent, investment logic map | hype pitch style |
| `sustainability-esg-report` | Sustainability ESG report | annual-report | ESG, sustainability, impact | green/white palette, landscape photography, soft arcs, impact metrics | generic leaf decoration |
| `impact-progress-report` | Impact progress report | annual-report | CSR, nonprofit, ESG | human photography, clean outcome cards, progress proof, soft neutrals | photo-only slides |
| `luxury-print-annual` | Luxury print annual | annual-report | premium enterprise annuals | paper texture, refined serif/sans pairing, thin rules, quiet color | low contrast microtype |

### Company, Product, And Launch

| style_id | style_name | aesthetic_family | Best for | Visual signature | Avoid |
|---|---|---|---|---|---|
| `apple-keynote-black` | Apple keynote black stage | keynote-launch | product launch, brand reveal | black field, oversized hero object, minimal copy, dramatic negative space | fake Apple assets or logos |
| `apple-keynote-white` | Apple keynote white clarity | keynote-launch | product, roadmap, feature release | white field, huge type, product hero, soft shadow, few decisive points | generic SaaS cards |
| `notion-workspace-clean` | Notion workspace clean | workspace-minimal | knowledge base, docs, internal tools | white canvas, block rhythm, light gray dividers, simple icons, database-like clarity | dull blank slides |
| `linear-axis-black` | Linear-style black axis | product-technical | SaaS, AI product, developer tools | black field, luminous mesh/wave, precise type, thin product-system lines | neon cyberpunk |
| `enterprise-saas-blue` | Enterprise SaaS blue | product-technical | B2B SaaS, platform, cloud | blue/white corporate gradients, product panels, metric strip, system architecture | default tech template |
| `mobile-app-launch-clean` | Mobile app launch clean | product-launch | app, feature launch | soft gradient arcs, phone/app surface placeholders, friendly icons, adoption proof | fake UI details |
| `certification-compliance-suite` | Certification compliance suite | product-launch | compliance, security, certification | trust badges, blue footer, certification seal area, structured proof | invented awards |
| `corporate-profile-architectural` | Corporate architectural profile | company-profile | company intro, capability deck | building/architecture hero, blue-gray geometry, KPI footer, strong corporate identity | fake office photos |
| `corporate-team-collaboration` | Corporate team collaboration | company-profile | culture, hiring, collaboration | bright white, human photo, light blue arcs, team value modules | stock-like diversity theater |
| `brand-proposal-minimal` | Minimal brand proposal | brand-proposal | brand, marketing, proposal | large photo block, sparse copy, vertical title, subdued palette | content-light prettiness |
| `nordic-business-future` | Nordic business future | company-profile | corporate future, innovation | clean blue architecture, cold light, vertical wordmark, open whitespace | visual coldness without warmth |
| `business-strategy-illustrated` | Strategy illustrated | company-profile | strategy, transformation | bold red/orange illustration, hand-cut paper feel, energetic business metaphors | changing the strategy story |

### Technical, AI, And Data Systems

| style_id | style_name | aesthetic_family | Best for | Visual signature | Avoid |
|---|---|---|---|---|---|
| `technical-schematic-premium` | Premium technical schematic | technical-schematic | AI, model, architecture, risk | precise grid, measured connectors, thin blue/gray lines, instrument annotations | meaningless circuits |
| `ai-lab-schematic` | AI lab schematic | technical-schematic | AI agent, model validation, automation | central agent/object, orbiting modules, verification loops, crisp icon linework | robot mascots as decoration |
| `data-product-dashboard` | Data product dashboard | data-visual | analytics, KPI, ops review | high-density but controlled data cards, chart variety, exact metric hierarchy | calling it command center |
| `glass-os-interface` | Glass OS interface | glassmorphism-blur | product, AI, SaaS | frosted panels, layered system UI, luminous boundaries, high contrast text | blurred labels |
| `spatial-3d-product` | Spatial 3D product surface | spatial-3d | platform, product, PRD | isometric product object, subtle 3D panels, depth as architecture | toy-like 3D |
| `code-terminal-industrial` | Industrial code terminal | technical-schematic | developer tools, infra | black/gray terminal rhythm, monospaced labels, technical blocks, red/green accents | fake code walls |
| `aurora-gradient-tech` | Aurora gradient tech | technology-polish | AI, product, future tech | soft aurora gradients, abstract product light, large type, careful contrast | generic AI blobs |
| `blueprint-architecture` | Blueprint architecture | technical-schematic | system design, engineering | blueprint lines, white/blue grid, building/system overlays, rational spacing | unreadable blueprint microtext |
| `cyber-clean-grid` | Clean cyber grid | technical-schematic | security, AI, fintech | dark grid, cyan/green accents, crisp cards, no neon overload | hacker aesthetic |
| `model-lifecycle-map` | Model lifecycle visual system | technical-schematic | model governance, MLOps | lifecycle rings, data lineage, validation gates, monitoring loops | content labels replacing style |

### Industry Solution Styles

| style_id | style_name | aesthetic_family | Best for | Visual signature | Avoid |
|---|---|---|---|---|---|
| `architecture-studio-minimal` | Architecture studio minimal | industry-architecture | real estate, architecture, design | large building photography, beige/gray panels, precise margins, plan-like labels | generic real estate brochure |
| `real-estate-portfolio-blue` | Urban real estate portfolio | industry-architecture | property portfolio | cityscape arcs, muted blue, asset cards, investment metrics | stock skyline filler |
| `automotive-luxury-minimal` | Automotive luxury minimal | industry-automotive | automotive, mobility | large vehicle hero, beige/black luxury space, clean feature labels | fake brand assets |
| `healthcare-academic-red` | Healthcare academic red | industry-healthcare | healthcare, medical, life science | clinical white, institutional red, evidence boxes, medical photo zone | alarmist red overload |
| `industrial-manufacturing-blue` | Industrial manufacturing blue | industry-manufacturing | manufacturing, materials | blue industrial photography, hex/grid structures, process proof | excessive machinery clutter |
| `logistics-system-green` | Logistics system green | industry-logistics | supply chain, logistics | route maps, nodes, green/teal flow lines, container/warehouse imagery | unreadable route spaghetti |
| `clean-energy-wave` | Clean energy wave | industry-energy | energy, sustainability | blue wave fields, turbine/landscape photos, clean infrastructure metrics | generic greenwashing |
| `fintech-growth-arrow` | Fintech growth arrow | industry-finance | fintech, finance platform | white/gold arrows, product metric strip, precise financial modules | "growth" as story rewrite |
| `retail-consumer-green` | Retail consumer green | industry-retail | retail, consumer operations | circular consumer value map, soft green, product/lifestyle photo pairing | lifestyle without operations proof |
| `hospitality-experience` | Hospitality experience | industry-hospitality | hotel, travel, service | warm interiors, premium photo panels, experience journey modules | travel brochure only |

### Education, Academic, And Training

| style_id | style_name | aesthetic_family | Best for | Visual signature | Avoid |
|---|---|---|---|---|---|
| `university-academic-formal` | University academic formal | academic | academic report, university deck | institutional color block, campus image, research badges, formal typography | fake university marks |
| `thesis-defense-clean` | Thesis defense clean | academic | thesis, defense, research | calm cover, clear structure, methodology diagrams, source discipline | decoration over method |
| `rigorous-academic-defense` | Rigorous academic defense | academic | thesis defense, dissertation, research defense | argument spine, literature/method/result logic, citation discipline, restrained institutional palette | consulting report framing |
| `conference-dark-stage` | Conference dark stage | academic | conference keynote | black stage, strong headline, minimal footer, speaker info, dramatic object | low contrast body copy |
| `lecture-minimal-white` | Minimal lecture white | academic | class, training, workshop | white field, centered title, thin rules, sparse didactic visuals | empty slide syndrome |
| `math-classroom-illustration` | Classroom illustration | education-playful | education, children, learning | friendly animals/objects, warm palette, large labels | childish style for adult decks |
| `training-tech-blue` | Training tech blue | training | onboarding, internal training | bright office photo, blue arcs, module steps, learning path | generic onboarding stock |
| `public-course-live` | Public course live | training | webinar, public class | gradient media controls, presenter card, schedule modules | fake livestream UI |
| `classical-civilization` | Classical civilization | academic-humanities | humanities, history | historical imagery, warm earth tones, serif titles, map/period motifs | museum pastiche |
| `research-seminar-wave` | Research seminar wave | academic | seminar, workshop | white, thin blue wave/particles, precise title block | illegible formulas as art |
| `grant-report-institutional` | Institutional grant report | academic | project grant, public fund | official-looking header, blue/green bands, conservative forms | invented seals |

### Creative, Editorial, Portfolio, And Brand

| style_id | style_name | aesthetic_family | Best for | Visual signature | Avoid |
|---|---|---|---|---|---|
| `editorial-gallery-white` | Editorial gallery white | editorial-gallery | portfolio, creative report | gallery numerals, editorial whitespace, image/object panels, serif/sans contrast | content without proof |
| `portfolio-museum-black` | Museum portfolio black | editorial-gallery | art, design, portfolio | black canvas, gallery object, sparse captions, cinematic crop | unreadable reversed text |
| `magazine-grid-modern` | Modern magazine grid | editorial-gallery | brand, culture, publication | strong magazine grid, photo collage, large issue numbers | cluttered collage |
| `vintage-serif-collage` | Vintage serif collage | vintage-editorial | culture, fashion, creative | serif headline, muted paper, illustration/photo collage, quiet texture | fake antique noise |
| `classical-european` | Classical European | classical | luxury, education, heritage | serif type, marble/stone, restrained gold, column-like spacing | kitsch gold ornaments |
| `kinfolk-lifestyle` | Kinfolk lifestyle | lifestyle-editorial | lifestyle, coffee, home, wellness | warm neutral photo, large whitespace, small captions, calm pacing | beige monotony |
| `tea-zen-natural` | Tea zen natural | lifestyle-editorial | wellness, culture, food | green tea photography, vertical Chinese title, quiet natural texture | unreadable vertical copy |
| `watercolor-villa` | Watercolor villa | lifestyle-editorial | architecture, travel, place | watercolor building, soft blue/green, sketch-like labels | muddy low contrast |
| `brutalist-monolith` | Brutalist monolith | brutalist | studio, architecture, art | black concrete, heavy typography, severe whitespace, stark imagery | oppressive density |
| `swiss-international` | Swiss international | editorial-gallery | design, corporate, culture | grid rigor, Helvetica-like type, strong alignment, limited color | default sterile slide |
| `neo-brutalist-color` | Neo-brutalist color | playful-editorial | creative, trends, culture | hard color blocks, black strokes, large type, poster energy | chaotic colors |
| `dot-matrix-object` | Dot-matrix object | experimental-editorial | creative, future, identity | stippled/dot object rendering, clean white space, vivid accent | noisy texture over text |

### Event, Lifestyle, And Personal

| style_id | style_name | aesthetic_family | Best for | Visual signature | Avoid |
|---|---|---|---|---|---|
| `red-gold-ceremony` | Red-gold ceremony | event-ceremony | annual meeting, awards, celebration | red stage light, gold type, celebratory glow, strong title center | overdone fireworks |
| `wedding-warm-luxury` | Wedding warm luxury | event-lifestyle | wedding, invitation, ceremony | cream/gold, floral or paper texture, soft photography | unreadable script |
| `new-chinese-cultural` | New Chinese cultural | cultural-editorial | festival, cultural event | elegant Chinese typography, heritage imagery, warm red/ink accents | cliché lantern overload |
| `travel-photo-album` | Travel photo album | travel-lifestyle | travel, campaign, city story | scrapbook photo collage, handwritten accent, natural paper | casual if audience is formal |
| `natural-exploration` | Natural exploration | travel-lifestyle | outdoor, environmental, tourism | full-bleed landscape, green data tags, adventure typography | stock travel poster only |
| `executive-resume-blue` | Executive resume blue | personal-brand | resume, self intro | blue diagonal, portrait circle, contact icon strip, clean resume hierarchy | fake portrait if none supplied |
| `promotion-defense-evidence` | Promotion defense evidence deck | personal-brand | promotion defense, capability review | achievement proof spine, role scope map, before/after impact, capability ladder, next-level plan | generic consulting loop |
| `personal-performance-review` | Personal performance review | personal-brand | personal performance, annual self review | timeline of wins, metric evidence, stakeholder map, reflective lessons, future commitments | vanity profile without proof |
| `interview-case-board` | Interview case board | personal-brand | interview presentation, case interview, panel review | question-to-answer board, concise evidence cards, decision recommendation, interviewer-ready hierarchy | dense annual report style |
| `creative-portfolio-dark` | Creative portfolio dark | personal-brand | portfolio, creator profile | dark gallery, object hero, large page number, curated samples | content-light vanity |
| `personal-brand-editorial` | Personal brand editorial | personal-brand | self intro, creator, consultant | editorial portrait, serif title, concise credential blocks | generic LinkedIn look |
| `lost-poster-documentary` | Documentary notice poster | lifestyle-utility | local poster, notice, community | poster typography, photo proof, contact strip, utility hierarchy | irrelevant to business decks |
| `holiday-illustration` | Holiday illustration | event-lifestyle | holiday, invitation, school | simple characters, festive palette, large readable label | childish in formal contexts |

## Combining Styles

Use one primary `style_id` per option. A secondary influence may be recorded as `secondary_style_influences`, but only when it does not blur the option:

- good: `mckinsey-consulting-report` with secondary `whitepaper-curve-pattern`
- good: `apple-keynote-white` with secondary `spatial-3d-product`
- risky: `notion-workspace-clean` plus `red-gold-ceremony`
- risky: `classical-european` plus `cyber-clean-grid`

When a user asks for "McKinsey style, annual report style, Apple keynote style, Notion style, minimalist style, promotion defense style, interview style, rigorous academic style, classical style", map them to:

- McKinsey style: `mckinsey-consulting-report`
- Enterprise annual report: `enterprise-annual-report` or `luxury-print-annual`
- Apple launch: `apple-keynote-black` or `apple-keynote-white`
- Notion style: `notion-workspace-clean`
- Minimalist style: `lecture-minimal-white`, `swiss-international`, or `brand-proposal-minimal`
- Promotion defense style: `promotion-defense-evidence` or `personal-performance-review`
- Interview style: `interview-case-board`
- Rigorous academic style: `rigorous-academic-defense` or `thesis-defense-clean`
- Classical style: `classical-european` or `shareholder-letter-editorial`
