import type { NextApiRequest, NextApiResponse } from "next";

const rootHandler = async (req: NextApiRequest, res: NextApiResponse) => {
    res.status(200).json({ message: "You're here." });
}

export default rootHandler;