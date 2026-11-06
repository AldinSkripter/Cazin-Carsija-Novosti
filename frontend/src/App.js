import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";
import { AuthProvider, SiteProvider } from "./lib/auth";
import PublicLayout from "./components/public/PublicLayout";
import Home from "./pages/public/Home";
import ArticlePage from "./pages/public/ArticlePage";
import ListingPage from "./pages/public/ListingPage";
import NotFound from "./pages/public/NotFound";
import { StaticPage, AuthorsPage, CamerasPage, NewsletterPage, SubmitNews } from "./pages/public/StaticPages";
import { AdminLayout, RequirePerm } from "./pages/admin/AdminLayout";
import Login, { ResetPassword } from "./pages/admin/Login";
import Dashboard from "./pages/admin/Dashboard";
import Articles from "./pages/admin/Articles";
import ArticleEditor from "./pages/admin/ArticleEditor";
import MediaPage from "./pages/admin/Media";
import HomeBuilder from "./pages/admin/HomeBuilder";
import { Categories, TagsPage, Breaking, Ads, PagesAdmin, Cameras } from "./pages/admin/CrudPages";
import { CommentsAdmin, Submissions, NewsletterAdmin } from "./pages/admin/Moderation";
import Users, { Profile } from "./pages/admin/Users";
import SettingsPage, { Audit, Analytics } from "./pages/admin/SettingsAudit";

const A = (perms, el) => <RequirePerm perms={perms}>{el}</RequirePerm>;

function App() {
  return (
    <AuthProvider>
      <SiteProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<PublicLayout />}>
              <Route path="/" element={<Home />} />
              <Route path="/vijesti/:slug" element={<ArticlePage />} />
              <Route path="/kategorija/:slug" element={<ListingPage mode="category" />} />
              <Route path="/tema/:tag" element={<ListingPage mode="tag" />} />
              <Route path="/autor/:slug" element={<ListingPage mode="author" />} />
              <Route path="/pretraga" element={<ListingPage mode="search" />} />
              <Route path="/arhiva" element={<ListingPage mode="archive" />} />
              <Route path="/autori" element={<AuthorsPage />} />
              <Route path="/stranica/:slug" element={<StaticPage />} />
              <Route path="/kamere" element={<CamerasPage />} />
              <Route path="/prijavite-vijest" element={<SubmitNews />} />
              <Route path="/newsletter" element={<NewsletterPage />} />
              <Route path="*" element={<NotFound />} />
            </Route>
            <Route path="/admin/prijava" element={<Login />} />
            <Route path="/admin/reset-lozinke" element={<ResetPassword />} />
            <Route path="/admin" element={<AdminLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="clanci" element={A(["articles.create", "articles.edit_own", "articles.edit_all"], <Articles />)} />
              <Route path="clanci/:id" element={A(["articles.create", "articles.edit_own", "articles.edit_all"], <ArticleEditor />)} />
              <Route path="kategorije" element={A(["categories.manage"], <Categories />)} />
              <Route path="oznake" element={A(["categories.manage"], <TagsPage />)} />
              <Route path="mediji" element={A(["media.manage", "articles.create"], <MediaPage />)} />
              <Route path="pocetna" element={A(["homepage.manage"], <HomeBuilder />)} />
              <Route path="breaking" element={A(["breaking.manage"], <Breaking />)} />
              <Route path="reklame" element={A(["ads.manage"], <Ads />)} />
              <Route path="komentari" element={A(["comments.moderate"], <CommentsAdmin />)} />
              <Route path="prijave" element={A(["submissions.manage"], <Submissions />)} />
              <Route path="newsletter" element={A(["newsletter.manage"], <NewsletterAdmin />)} />
              <Route path="kamere" element={A(["cameras.manage"], <Cameras />)} />
              <Route path="stranice" element={A(["pages.manage"], <PagesAdmin />)} />
              <Route path="statistika" element={A(["analytics.view"], <Analytics />)} />
              <Route path="korisnici" element={A(["users.manage"], <Users />)} />
              <Route path="audit" element={A(["audit.view"], <Audit />)} />
              <Route path="postavke" element={A(["settings.manage"], <SettingsPage />)} />
              <Route path="profil" element={<Profile />} />
            </Route>
          </Routes>
        </BrowserRouter>
        <Toaster richColors position="top-right" />
      </SiteProvider>
    </AuthProvider>
  );
}

export default App;
