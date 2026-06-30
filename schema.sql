-- Database: ecommerce_db
CREATE DATABASE IF NOT EXISTS `ecommerce_db` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `ecommerce_db`;

-- Table structure for table `products`
DROP TABLE IF EXISTS `products`;
CREATE TABLE `products` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(255) NOT NULL,
  `description` TEXT DEFAULT NULL,
  `price` DECIMAL(10,2) NOT NULL,
  `stock` INT NOT NULL DEFAULT 0,
  `category` VARCHAR(100) DEFAULT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Sample data: SonoLight professional lighting & DJ equipment
INSERT INTO `products` (`name`, `description`, `price`, `stock`, `category`) VALUES
('Beam 230W 7R Moving Head', 'Lyre Beam motorisée 230W avec prisme rotatif, gobos et effets stroboscopiques. Idéale pour clubs et concerts.', 2500.00, 12, 'Moving Heads'),
('LED Par 18x18W RGBWA+UV', 'Projecteur LED Par slim 6-en-1 avec DMX512, parfait pour éclairage de scène et ambiance événementielle.', 450.00, 35, 'Éclairage LED'),
('Laser RGB 5W Animation', 'Laser d''animation multicolore 5W avec contrôle ILDA et DMX. Effets laser spectaculaires pour shows et discothèques.', 3800.00, 8, 'Lasers'),
('Wash LED 36x18W RGBWA+UV', 'Lyre Wash LED haute puissance avec zoom 15-60°. Couverture large et mélange de couleurs fluide.', 1800.00, 15, 'Moving Heads'),
('Flat Par 12x12W RGBWA+UV', 'Projecteur Par LED ultra-plat avec batterie rechargeable et contrôle sans fil. Parfait pour mariages et événements.', 350.00, 50, 'Éclairage LED'),
('Machine à Fumée 3000W DMX', 'Machine à fumée professionnelle avec sortie verticale et contrôle DMX. Effet brouillard dense pour scènes et clubs.', 1200.00, 20, 'Effets Spéciaux'),
('Spider LED 8x12W RGBW', 'Effet araignée LED motorisé à faisceaux multiples. Mouvements rapides et effets dynamiques pour pistes de danse.', 750.00, 25, 'Effets Spéciaux'),
('Waterproof Par 18x18W IP65', 'Projecteur LED étanche IP65 pour événements extérieurs. Résistant à la pluie et à la poussière.', 650.00, 18, 'Éclairage Extérieur'),
('Contrôleur DMX 512 Pro', 'Console DMX 512 canaux avec écran tactile et interface intuitive. Compatible avec tous les appareils DMX.', 900.00, 30, 'Accessoires'),
('Follow Spot 330W', 'Poursuite professionnelle 330W avec iris, gobos et variation de couleurs. Portée jusqu''à 50 mètres.', 2200.00, 6, 'Éclairage Scénique');
