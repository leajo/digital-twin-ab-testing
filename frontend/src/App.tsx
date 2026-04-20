import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import UploadPage from "./pages/UploadPage";
import SimulatePage from "./pages/SimulatePage";
import ReportPage from "./pages/ReportPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<UploadPage />} />
          <Route path="/simulate" element={<SimulatePage />} />
          <Route path="/report/:id" element={<ReportPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
