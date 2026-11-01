import RealPlayerExperience from "../components/RealPlayerExperience.jsx";
import { loadExperimentalRatings, experimentalModels, validateExperimentalPlayer } from "./experimentalDelivery.js";
export default function FiveAttributeExperimentalExperience(props) {
  return <RealPlayerExperience {...props} local loadRatings={loadExperimentalRatings} models={experimentalModels} validatePlayer={validateExperimentalPlayer} />;
}
